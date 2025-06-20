"""
SQLAlchemy ORM models for the USA Triathlon Talent ID Pipeline.

This module defines the database schema using SQLAlchemy declarative syntax.
All models include proper relationships, indexes, and constraints.

Entity Relationship Overview:
- Runner: NCAA track athletes scraped from TFRRS
- TimeStandard: USA Triathlon performance benchmarks
- Classification: Performance classification results against standards

Database Design Notes:
- All times stored as DECIMAL seconds for precision
- Names normalized to lowercase for consistent matching
- Timestamps track data freshness for cache invalidation
- JSONB fields store raw scraped data for debugging/re-processing
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import os

from sqlalchemy import (
    ARRAY, Column, DateTime, ForeignKey, Integer, String, Text, DECIMAL, 
    Index, UniqueConstraint, CheckConstraint, Boolean, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Database-agnostic JSON type
def get_json_type():
    """Return appropriate JSON type based on database URL."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///C:/Users/jhigh/OneDrive/Personal Projects/Databases/tri_talent.db")
    if database_url.startswith("postgresql"):
        return JSONB
    else:
        return JSON

def get_array_type():
    """Return appropriate array type based on database URL."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///C:/Users/jhigh/OneDrive/Personal Projects/Databases/tri_talent.db")
    if database_url.startswith("postgresql"):
        return ARRAY(String)
    else:
        return JSON  # Store arrays as JSON in SQLite


class Runner(Base):
    """
    NCAA Division I track athletes scraped from TFRRS.
    
    Stores athlete performance data and metadata for matching against swimmers.
    Performance times are normalized to seconds for consistent comparison.
    """
    __tablename__ = "runners"
    
    # Primary key
    runner_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Athlete identification (normalized for matching)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    
    # Performance data
    college_team = Column(String(200), nullable=False)
    event = Column(String(50), nullable=False)  # e.g., "800m_outdoor", "Mile_indoor"
    performance_time = Column(DECIMAL(8, 2), nullable=False)  # Seconds with 2 decimal precision
    year = Column(Integer, nullable=False)
    gender = Column(String(1), nullable=False)  # 'M' or 'F'
    
    # Optional enrichment data (may be populated later)
    hometown = Column(String(200))
    birth_year = Column(Integer)
    
    # New fields for AI agent output
    high_school = Column(String(200))
    class_year = Column(String(50))  # e.g., "Senior", "Junior"
    swimmer = Column(String(10))  # "Yes" or "No"
    score = Column(Integer)  # 0-100
    match_confidence = Column(String(20))  # "Low", "Medium", "High"
    
    # Metadata
    scrape_timestamp = Column(DateTime, nullable=False, default=func.now())
    raw_data = Column(get_json_type())  # Store original scraped HTML/data for debugging
    
    # Constraints
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F')", name="valid_gender"),
        CheckConstraint("performance_time > 0", name="positive_time"),
        CheckConstraint("year >= 2000 AND year <= 2030", name="valid_year"),
        Index("idx_runner_name", "last_name", "first_name"),
        Index("idx_runner_event_year", "event", "year"),
        Index("idx_runner_team", "college_team"),
        UniqueConstraint('first_name', 'last_name', name='uq_runner_identity'),
    )
    
    def __repr__(self) -> str:
        return f"<Runner(id={self.runner_id}, name='{self.first_name} {self.last_name}', event='{self.event}')>"


class TimeStandard(Base):
    """
    USA Triathlon performance standards for classification.
    
    Stores cutoff times for different performance tiers across various events.
    Supports both swimming and running events with gender/age group specificity.
    """
    __tablename__ = "time_standards"
    
    # Primary key
    standard_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Classification criteria
    gender = Column(String(1), nullable=False)  # 'M' or 'F'
    age_group = Column(String(50), nullable=False)  # "Junior", "Open", etc.
    event = Column(String(100), nullable=False)  # "200_Free_LCM", "5k_Run", etc.
    category = Column(String(50), nullable=False)  # "World Leading", "Internationally Ranked", etc.
    
    # Performance threshold
    cutoff_seconds = Column(DECIMAL(8, 2), nullable=False)
    
    # Metadata for reporting
    color_code = Column(String(20))  # "Dark_Green", "Green", "Yellow", "Red"
    display_order = Column(Integer, default=0)  # For consistent sorting
    
    # Relationships
    classifications = relationship("Classification", back_populates="standard")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F')", name="valid_standard_gender"),
        CheckConstraint("cutoff_seconds > 0", name="positive_cutoff"),
        UniqueConstraint("gender", "age_group", "event", "category", name="unique_standard"),
        Index("idx_standard_lookup", "gender", "event", "category"),
    )
    
    def __repr__(self) -> str:
        return f"<TimeStandard(id={self.standard_id}, event='{self.event}', category='{self.category}')>"


class Classification(Base):
    """
    Performance classification results against USA Triathlon standards.
    
    Links verified runner-swimmer matches to their performance tier based on
    swimming times compared against USA Triathlon benchmarks.
    """
    __tablename__ = "classification"
    
    # Primary key
    class_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    standard_id = Column(Integer, ForeignKey("time_standards.standard_id"), nullable=False)
    
    # Classification results
    event_classified = Column(String(100), nullable=False)  # Which swimming event was classified
    athlete_time = Column(DECIMAL(8, 2), nullable=False)  # Athlete's actual time in seconds
    standard_time = Column(DECIMAL(8, 2), nullable=False)  # Standard cutoff time
    category_assigned = Column(String(50), nullable=False)  # "World Leading", etc.
    color_label = Column(String(20), nullable=False)  # "Dark_Green", "Green", "Yellow", "Red"
    
    # Performance analysis
    time_differential = Column(DECIMAL(8, 2))  # How much faster/slower than standard
    percentile_rank = Column(DECIMAL(5, 2))  # Optional: rank within category
    
    # Metadata
    classification_timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # Relationships
    standard = relationship("TimeStandard", back_populates="classifications")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("athlete_time > 0", name="positive_athlete_time"),
        CheckConstraint("standard_time > 0", name="positive_standard_time"),
        Index("idx_classification_category", "category_assigned"),
        Index("idx_classification_event", "event_classified"),
    )
    
    def __repr__(self) -> str:
        return f"<Classification(id={self.class_id}, category='{self.category_assigned}', event='{self.event_classified}')>"
