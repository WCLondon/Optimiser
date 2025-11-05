"""
Database connection helper for promoter form
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from functools import lru_cache

from config import get_settings


@lru_cache()
def get_db_engine() -> Engine:
    """
    Get or create SQLAlchemy engine for database connections
    
    Returns:
        SQLAlchemy Engine instance
    """
    settings = get_settings()
    
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
        echo=False
    )
    
    return engine
