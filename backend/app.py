"""
FastAPI backend for BNG Optimiser - Job queue and caching service
Handles heavy optimization computations in background workers
"""

import hashlib
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis
from rq import Queue
from rq.job import Job

# Initialize FastAPI app
app = FastAPI(
    title="BNG Optimiser Backend",
    description="Background job processing and caching for BNG optimization",
    version="1.0.0"
)

# Add CORS middleware to allow Streamlit frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=False)
job_queue = Queue("jobs", connection=redis_conn)

# Cache TTL in seconds (12 hours)
CACHE_TTL = int(os.getenv("CACHE_TTL", "43200"))


# Pydantic models
class JobInput(BaseModel):
    """Input parameters for optimization job"""
    demand_df: Dict[str, Any] = Field(..., description="Demand DataFrame as dict")
    target_lpa: str = Field("", description="Target LPA name")
    target_nca: str = Field("", description="Target NCA name")
    lpa_neighbors: list = Field(default_factory=list)
    nca_neighbors: list = Field(default_factory=list)
    lpa_neighbors_norm: list = Field(default_factory=list)
    nca_neighbors_norm: list = Field(default_factory=list)
    quotes_hold_policy: str = Field("Ignore quotes (default)")
    promoter_info: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "demand_df": {"habitat_name": ["Grassland"], "units_required": [10.0]},
                "target_lpa": "Winchester",
                "target_nca": "South Downs",
                "lpa_neighbors": [],
                "nca_neighbors": [],
                "lpa_neighbors_norm": [],
                "nca_neighbors_norm": [],
                "quotes_hold_policy": "Ignore quotes (default)",
                "promoter_info": None
            }
        }


class JobResponse(BaseModel):
    """Response for job creation or status"""
    job_id: Optional[str] = None
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cached: bool = False


def hash_inputs(params: Dict[str, Any]) -> str:
    """
    Create deterministic hash of input parameters for caching
    
    Args:
        params: Dictionary of input parameters
        
    Returns:
        SHA256 hash of sorted JSON representation
    """
    # Create a canonical representation by sorting keys
    canonical = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached result from Redis
    
    Args:
        cache_key: Cache key (hash of inputs)
        
    Returns:
        Cached result dict or None
    """
    try:
        cached = redis_conn.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        print(f"Cache retrieval error: {e}")
    return None


def set_cached_result(cache_key: str, result: Dict[str, Any], ttl: int = CACHE_TTL):
    """
    Store result in Redis cache
    
    Args:
        cache_key: Cache key (hash of inputs)
        result: Result dictionary to cache
        ttl: Time-to-live in seconds
    """
    try:
        redis_conn.setex(cache_key, ttl, json.dumps(result, default=str))
    except Exception as e:
        print(f"Cache storage error: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_conn.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/jobs", response_model=JobResponse)
async def create_job(job_input: JobInput):
    """
    Create a new optimization job or return cached result
    
    Args:
        job_input: Job parameters
        
    Returns:
        JobResponse with job_id or cached result
    """
    try:
        # Convert input to dict for hashing
        params_dict = job_input.model_dump()
        
        # Generate cache key
        cache_key = f"cache:{hash_inputs(params_dict)}"
        
        # Check if result is already cached
        cached_result = get_cached_result(cache_key)
        if cached_result:
            return JobResponse(
                job_id=None,
                status="finished",
                result=cached_result,
                cached=True
            )
        
        # Import task function (avoid circular import)
        from tasks import run_optimization
        
        # Enqueue job
        job = job_queue.enqueue(
            run_optimization,
            params_dict,
            job_timeout='10m',  # 10 minute timeout for optimization
            result_ttl=CACHE_TTL,  # Keep result for cache TTL duration
            meta={'cache_key': cache_key}  # Store cache key in job metadata
        )
        
        return JobResponse(
            job_id=job.get_id(),
            status="queued",
            cached=False
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job creation failed: {str(e)}")


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get status and result of a job
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobResponse with current status and result if finished
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        if job.is_finished:
            result = job.result
            
            # Cache the result if we have a cache key
            cache_key = job.meta.get('cache_key')
            if cache_key and result:
                set_cached_result(cache_key, result)
            
            return JobResponse(
                job_id=job_id,
                status="finished",
                result=result
            )
        
        elif job.is_failed:
            return JobResponse(
                job_id=job_id,
                status="failed",
                error=str(job.exc_info) if job.exc_info else "Unknown error"
            )
        
        elif job.is_started:
            return JobResponse(
                job_id=job_id,
                status="started"
            )
        
        elif job.is_queued:
            return JobResponse(
                job_id=job_id,
                status="queued"
            )
        
        else:
            return JobResponse(
                job_id=job_id,
                status="unknown"
            )
            
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")


@app.delete("/cache/{cache_key}")
async def clear_cache_entry(cache_key: str):
    """
    Clear a specific cache entry
    
    Args:
        cache_key: Cache key to clear
        
    Returns:
        Success status
    """
    try:
        deleted = redis_conn.delete(f"cache:{cache_key}")
        return {"deleted": bool(deleted)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


@app.post("/cache/clear-all")
async def clear_all_cache():
    """
    Clear all cached results
    
    Returns:
        Number of keys deleted
    """
    try:
        keys = redis_conn.keys("cache:*")
        if keys:
            deleted = redis_conn.delete(*keys)
            return {"deleted": deleted}
        return {"deleted": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
