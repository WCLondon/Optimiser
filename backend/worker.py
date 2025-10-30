"""
RQ Worker for processing background jobs.

Run this worker to process optimization jobs from the Redis queue.
"""
import os
import redis
import rq

# Initialize Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

if __name__ == "__main__":
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    w = rq.Worker(["jobs"], connection=r)
    print(f"Starting RQ worker, listening on 'jobs' queue...")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    w.work()
