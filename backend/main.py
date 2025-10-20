"""
FastAPI backend for BNG Optimiser - Attio App integration.

This server provides REST endpoints for running quote optimizations,
checking job status, and integrating with Attio's Assert Record API.
"""

import os
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

from optimiser_core import run_quote

# Initialize FastAPI app
app = FastAPI(
    title="BNG Optimiser API",
    description="Backend API for BNG Optimiser Attio App",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
ATTIO_API_KEY = os.getenv("ATTIO_API_KEY", "")
ATTIO_API_URL = os.getenv("ATTIO_API_URL", "https://api.attio.com/v2")


# Job status enum
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# In-memory job storage (use Redis or database in production)
jobs_store: Dict[str, Dict[str, Any]] = {}


# Pydantic models
class DemandItem(BaseModel):
    habitat_name: str
    units: float


class LocationInfo(BaseModel):
    postcode: Optional[str] = None
    address: Optional[str] = None
    lpa_name: Optional[str] = None
    nca_name: Optional[str] = None


class RunQuoteRequest(BaseModel):
    record_id: Optional[str] = Field(None, description="Attio record ID")
    demand: list[DemandItem]
    location: Optional[LocationInfo] = None
    backend_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Backend data (Banks, Pricing, etc.). If not provided, uses default/cached data"
    )
    contract_size: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class SaveToAttioRequest(BaseModel):
    record_id: str
    quote_results: Dict[str, Any]
    object_type: str = Field("quote", description="Attio object type to save to")


# Health check
@app.get("/")
async def root():
    return {
        "service": "BNG Optimiser API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Run quote endpoint
@app.post("/run", response_model=Dict[str, str])
async def run_quote_endpoint(
    request: RunQuoteRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a quote optimization job.
    
    Returns a job_id that can be used to poll for status.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    jobs_store[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "progress": "Job queued",
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "request": request.dict()
    }
    
    # Start background task
    background_tasks.add_task(process_quote_job, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job started"
    }


async def process_quote_job(job_id: str, request: RunQuoteRequest):
    """
    Background task to process the quote optimization.
    """
    try:
        # Update status to running
        jobs_store[job_id]["status"] = JobStatus.RUNNING
        jobs_store[job_id]["progress"] = "Running optimization..."
        jobs_store[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Prepare payload for run_quote
        payload = {
            "demand": [d.dict() for d in request.demand],
            "backend_data": request.backend_data or get_default_backend_data(),
            "location": request.location.dict() if request.location else {},
            "contract_size": request.contract_size,
            "options": request.options or {}
        }
        
        # Run optimization (blocking call, but in background task)
        result = await asyncio.to_thread(run_quote, payload)
        
        # Update job with result
        if result.get("success"):
            jobs_store[job_id]["status"] = JobStatus.COMPLETED
            jobs_store[job_id]["result"] = result
            jobs_store[job_id]["progress"] = "Optimization completed successfully"
        else:
            jobs_store[job_id]["status"] = JobStatus.FAILED
            jobs_store[job_id]["error"] = result.get("error", "Unknown error")
            jobs_store[job_id]["progress"] = "Optimization failed"
        
        jobs_store[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        jobs_store[job_id]["status"] = JobStatus.FAILED
        jobs_store[job_id]["error"] = str(e)
        jobs_store[job_id]["progress"] = "Job failed with exception"
        jobs_store[job_id]["updated_at"] = datetime.utcnow().isoformat()


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a running job.
    """
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs_store[job_id]


@app.post("/save")
async def save_to_attio(request: SaveToAttioRequest):
    """
    Save quote results to Attio using Assert Record API.
    
    This endpoint takes the quote results and upserts them to an Attio
    record using the Assert Record endpoint for idempotent writes.
    """
    if not ATTIO_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Attio API key not configured"
        )
    
    try:
        # Map quote results to Attio record format
        record_data = map_quote_to_attio_record(
            request.quote_results,
            request.object_type
        )
        
        # Call Attio Assert Record API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ATTIO_API_URL}/objects/{request.object_type}/records",
                headers={
                    "Authorization": f"Bearer {ATTIO_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=record_data,
                timeout=30.0
            )
            
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Attio API error: {response.text}"
                )
            
            return {
                "success": True,
                "record": response.json(),
                "message": "Quote saved to Attio successfully"
            }
    
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to communicate with Attio API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving to Attio: {str(e)}"
        )


def map_quote_to_attio_record(
    quote_results: Dict[str, Any],
    object_type: str
) -> Dict[str, Any]:
    """
    Map quote results to Attio record format.
    
    This is where we define the mapping between our quote data
    and Attio's data model.
    """
    # Example mapping - adjust based on actual Attio schema
    record = {
        "data": {
            "values": {
                "total_cost": quote_results.get("total_cost", 0),
                "contract_size": quote_results.get("contract_size", ""),
                "allocation_count": len(quote_results.get("allocations", [])),
                "quote_date": datetime.utcnow().isoformat(),
            }
        }
    }
    
    # Add allocation details as JSON if available
    if quote_results.get("allocations"):
        record["data"]["values"]["allocations_json"] = quote_results["allocations"]
    
    if quote_results.get("summary"):
        record["data"]["values"]["summary"] = quote_results["summary"]
    
    return record


def get_default_backend_data() -> Dict[str, Any]:
    """
    Load default backend data from cached source.
    
    In production, this would load from a file, database, or cache.
    For now, returns empty structure.
    """
    # TODO: Implement backend data loading from Excel file or database
    return {
        "Banks": [],
        "Pricing": [],
        "HabitatCatalog": [],
        "Stock": []
    }


# Additional endpoints for debugging/development
@app.get("/jobs")
async def list_jobs():
    """List all jobs (for debugging)"""
    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job["status"],
                "created_at": job["created_at"]
            }
            for job_id, job in jobs_store.items()
        ]
    }


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job (for debugging)"""
    if job_id in jobs_store:
        del jobs_store[job_id]
        return {"message": "Job deleted"}
    raise HTTPException(status_code=404, detail="Job not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
