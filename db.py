"""
Database connection management for PostgreSQL via SQLAlchemy.
Handles connection pooling, retries, and health checks.
"""

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL database connections using SQLAlchemy."""
    
    _engine: Optional[Engine] = None
    
    @classmethod
    def get_engine(cls) -> Engine:
        """
        Get or create the SQLAlchemy engine.
        Reads connection string from environment variable.
        """
        if cls._engine is None:
            # Get database URL from environment variable
            db_url = os.getenv("DATABASE_URL")
            
            # Fallback: try to load from Streamlit secrets if available
            if not db_url:
                try:
                    import streamlit as st
                    db_url = st.secrets.get("database", {}).get("url")
                except ImportError:
                    pass
            
            if not db_url:
                raise ValueError(
                    "Database URL not found. "
                    "Please set DATABASE_URL environment variable or configure in secrets"
                )
            
            # Create engine with connection pooling
            cls._engine = create_engine(
                db_url,
                pool_pre_ping=True,  # Verify connections before using them
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=False,  # Set to True for SQL debugging
            )
            
            # Add event listener to set search_path if needed
            @event.listens_for(cls._engine, "connect")
            def receive_connect(dbapi_conn, connection_record):
                """Set session parameters on new connections."""
                pass  # Can add custom session setup here if needed
            
        return cls._engine
    
    @classmethod
    def close(cls):
        """Close and dispose of the engine."""
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
    
    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def execute_with_retry(cls, query, params=None):
        """
        Execute a query with automatic retry on transient failures.
        
        Args:
            query: SQL query string or SQLAlchemy text object
            params: Optional parameters for the query
        
        Returns:
            Result of the query execution
        """
        engine = cls.get_engine()
        with engine.connect() as conn:
            if isinstance(query, str):
                query = text(query)
            result = conn.execute(query, params or {})
            conn.commit()
            return result
    
    @classmethod
    def db_healthcheck(cls) -> bool:
        """
        Perform a basic connectivity test to the database.
        
        Returns:
            True if the database is accessible, False otherwise
        """
        try:
            engine = cls.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
