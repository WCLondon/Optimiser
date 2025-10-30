"""
Backend integration module for BNG Optimiser Streamlit app
Provides functions to interact with the FastAPI backend when available
"""

import os
import time
import json
import hashlib
from typing import Dict, Any, Optional, Tuple
import requests
import pandas as pd
import streamlit as st


# Backend configuration
BACKEND_URL = os.getenv("BACKEND_URL", "")
BACKEND_ENABLED = bool(BACKEND_URL)


def hash_inputs(params: Dict[str, Any]) -> str:
    """
    Create deterministic hash of input parameters for caching
    
    Args:
        params: Dictionary of input parameters
        
    Returns:
        SHA256 hash of sorted JSON representation
    """
    canonical = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@st.cache_data(show_spinner=False, ttl=3600)
def call_backend_cached(params_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Cached wrapper for backend API calls
    Uses Streamlit's caching to avoid repeated API calls with same inputs
    
    Args:
        params_dict: Parameters dictionary
        
    Returns:
        Result dictionary or None if failed
    """
    if not BACKEND_ENABLED:
        return None
    
    try:
        # Create job
        response = requests.post(
            f"{BACKEND_URL}/jobs",
            json=params_dict,
            timeout=30
        )
        response.raise_for_status()
        job_info = response.json()
        
        # If already cached, return immediately
        if job_info.get("cached"):
            return job_info.get("result")
        
        # Otherwise, poll for result
        job_id = job_info.get("job_id")
        if not job_id:
            return None
        
        return poll_job_result(job_id)
        
    except Exception as e:
        st.error(f"Backend API error: {e}")
        return None


def poll_job_result(job_id: str, max_wait: int = 300) -> Optional[Dict[str, Any]]:
    """
    Poll backend for job result
    
    Args:
        job_id: Job identifier
        max_wait: Maximum time to wait in seconds
        
    Returns:
        Result dictionary or None if failed/timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{BACKEND_URL}/jobs/{job_id}", timeout=10)
            response.raise_for_status()
            job_status = response.json()
            
            status = job_status.get("status")
            
            if status == "finished":
                return job_status.get("result")
            elif status == "failed":
                error = job_status.get("error", "Unknown error")
                st.error(f"Job failed: {error}")
                return None
            
            # Still processing, wait a bit
            time.sleep(1.0)
            
        except Exception as e:
            st.error(f"Error polling job: {e}")
            return None
    
    st.warning("Job timed out after {max_wait} seconds")
    return None


def submit_optimization_job(
    demand_df: pd.DataFrame,
    target_lpa: str,
    target_nca: str,
    lpa_neighbors: list,
    nca_neighbors: list,
    lpa_neighbors_norm: list,
    nca_neighbors_norm: list,
    quotes_hold_policy: str = "Ignore quotes (default)",
    promoter_info: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Submit optimization job to backend or return cached result
    
    Returns:
        Tuple of (job_id, cached_result)
        If cached_result is not None, use it immediately
        If job_id is not None, poll for result
    """
    if not BACKEND_ENABLED:
        return None, None
    
    try:
        # Convert DataFrame to dict for serialization
        demand_dict = demand_df.to_dict(orient='list')
        
        params = {
            "demand_df": demand_dict,
            "target_lpa": target_lpa,
            "target_nca": target_nca,
            "lpa_neighbors": lpa_neighbors,
            "nca_neighbors": nca_neighbors,
            "lpa_neighbors_norm": lpa_neighbors_norm,
            "nca_neighbors_norm": nca_neighbors_norm,
            "quotes_hold_policy": quotes_hold_policy,
            "promoter_info": promoter_info
        }
        
        response = requests.post(
            f"{BACKEND_URL}/jobs",
            json=params,
            timeout=30
        )
        response.raise_for_status()
        job_info = response.json()
        
        if job_info.get("cached"):
            return None, job_info.get("result")
        
        return job_info.get("job_id"), None
        
    except Exception as e:
        st.error(f"Error submitting job: {e}")
        return None, None


def check_job_status(job_id: str) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    """
    Check status of a job
    
    Returns:
        Tuple of (status, result, error)
    """
    if not BACKEND_ENABLED or not job_id:
        return "unknown", None, None
    
    try:
        response = requests.get(f"{BACKEND_URL}/jobs/{job_id}", timeout=10)
        response.raise_for_status()
        job_status = response.json()
        
        return (
            job_status.get("status", "unknown"),
            job_status.get("result"),
            job_status.get("error")
        )
        
    except Exception as e:
        return "error", None, str(e)


def check_backend_health() -> bool:
    """
    Check if backend is healthy and accessible
    
    Returns:
        True if backend is healthy, False otherwise
    """
    if not BACKEND_ENABLED:
        return False
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        response.raise_for_status()
        health = response.json()
        return health.get("status") == "ok"
    except Exception:
        return False


def show_backend_status():
    """
    Display backend connection status in sidebar
    """
    if BACKEND_ENABLED:
        with st.sidebar:
            st.markdown("---")
            st.markdown("**Backend Status**")
            if check_backend_health():
                st.success("✅ Connected")
            else:
                st.error("❌ Not responding")
            st.caption(f"URL: {BACKEND_URL}")
    else:
        with st.sidebar:
            st.markdown("---")
            st.info("ℹ️ Running in standalone mode (no backend)")


# Export configuration
__all__ = [
    "BACKEND_ENABLED",
    "submit_optimization_job",
    "check_job_status",
    "poll_job_result",
    "check_backend_health",
    "show_backend_status",
    "hash_inputs",
    "call_backend_cached"
]
