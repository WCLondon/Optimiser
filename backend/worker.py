"""
RQ Worker for BNG Optimiser background jobs
Processes optimization tasks from the Redis queue
"""

import os
import redis
from rq import Worker, Queue

# Redis connection configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

def main():
    """Start the RQ worker"""
    redis_conn = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=False
    )
    
    # Test connection
    try:
        redis_conn.ping()
        print(f"✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")
        return
    
    # Create worker for the 'jobs' queue
    worker = Worker(['jobs'], connection=redis_conn)
    print(f"✓ Worker started, listening on queue 'jobs'")
    print("Waiting for jobs...")
    worker.work()


if __name__ == "__main__":
    main()
