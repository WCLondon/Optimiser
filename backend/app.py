"""
FastAPI backend for BNG Optimiser - handles heavy computation in background workers.
"""
import hashlib
import json
import os
from typing import Any, Dict, Optional

import redis
import rq
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Initialize Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
q = rq.Queue("jobs", connection=r)

app = FastAPI(title="BNG Optimiser Backend", version="1.0.0")


class JobIn(BaseModel):
    """Input model for job submission."""
    params: Dict[str, Any]


class JobOut(BaseModel):
    """Output model for job status."""
    job_id: Optional[str] = None
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


def hash_inputs(d: Dict[str, Any]) -> str:
    """Generate deterministic hash for input parameters."""
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


@app.get("/health")
def health():
    """Health check endpoint."""
    try:
        r.ping()
        return {"ok": True, "redis": "connected"}
    except Exception:
        # Don't expose detailed error information to external users
        return {"ok": False, "redis": "disconnected"}


@app.post("/jobs", response_model=JobOut)
def create_job(job: JobIn):
    """
    Create a new optimization job.
    
    If the same inputs have been processed recently (cached in Redis),
    returns the cached result immediately without creating a new job.
    """
    # Generate cache key from input hash
    input_hash = hash_inputs(job.params)
    cache_key = f"cache:{input_hash}"
    
    # Check if result is cached
    cached = r.get(cache_key)
    if cached:
        return JobOut(
            job_id=None,
            status="finished",
            result=json.loads(cached)
        )
    
    # Import task here to avoid circular imports
    from tasks import run_optimization
    
    # Enqueue job
    rq_job = q.enqueue(run_optimization, job.params, job_timeout="10m")
    
    return JobOut(
        job_id=rq_job.get_id(),
        status="queued"
    )


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str):
    """
    Get status and result of a job.
    
    Returns:
        - queued: Job is waiting in queue
        - started: Job is being processed
        - finished: Job completed successfully
        - failed: Job failed with error
    """
    try:
        j = rq.job.Job.fetch(job_id, connection=r)
    except rq.exceptions.NoSuchJobError:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if j.is_finished:
        return JobOut(
            job_id=job_id,
            status="finished",
            result=j.result
        )
    
    if j.is_failed:
        # Don't expose detailed stack traces to external users
        return JobOut(
            job_id=job_id,
            status="failed",
            error="Job processing failed"
        )
    
    status = j.get_status()
    if status in ("queued", "started", "deferred"):
        return JobOut(
            job_id=job_id,
            status=status
        )
    
    raise HTTPException(status_code=500, detail=f"Unknown job status: {status}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
