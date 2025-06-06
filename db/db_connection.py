"""
Database connection management for the USA Triathlon Talent ID Pipeline.

This module provides database connection utilities using SQLAlchemy
with PostgreSQL, including connection pooling and session management.
"""

import os
from typing import Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tri_user:tri_password@localhost:5432/tri_talent_db")

# Connection pool configuration
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30


def create_db_engine() -> Engine:
    """
    Create a SQLAlchemy engine with connection pooling.
    
    Returns:
        Engine: Configured SQLAlchemy engine
    """
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_pre_ping=True,  # Verify connections before use
        echo=False  # Set to True for SQL query logging
    )
    return engine


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """
    Create a session factory for database operations.
    
    Args:
        engine: Optional SQLAlchemy engine. If None, creates a new one.
        
    Returns:
        sessionmaker: Session factory for creating database sessions
    """
    if engine is None:
        engine = create_db_engine()
        
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        Session: SQLAlchemy session for database operations
        
    Usage:
        session = get_db_session()
        try:
            # Database operations
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    """
    SessionFactory = get_session_factory()
    return SessionFactory()


# Global engine instance (created lazily)
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """
    Get the global database engine instance.
    
    Returns:
        Engine: Global SQLAlchemy engine
    """
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine
