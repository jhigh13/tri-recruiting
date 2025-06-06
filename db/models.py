"""
SQLAlchemy ORM models for the USA Triathlon Talent ID Pipeline.

This module defines the database schema using SQLAlchemy declarative syntax.
All models include proper relationships, indexes, and constraints.

Entity Relationship Overview:
- Runner: NCAA track athletes scraped from TFRRS
- Swimmer: Athletes with swimming background from SwimCloud  
- TimeStandard: USA Triathlon performance benchmarks
- RunnerSwimmerMatch: Links runners to potential swimmer matches with scoring
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
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/tri_talent.db")
    if database_url.startswith("postgresql"):
        return JSONB
    else:
        return JSON

def get_array_type():
    """Return appropriate array type based on database URL."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/tri_talent.db")
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
    
    # Metadata
    scrape_timestamp = Column(DateTime, nullable=False, default=func.now())
    raw_data = Column(get_json_type())  # Store original scraped HTML/data for debugging
    
    # Relationships
    matches = relationship("RunnerSwimmerMatch", back_populates="runner")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F')", name="valid_gender"),
        CheckConstraint("performance_time > 0", name="positive_time"),
        CheckConstraint("year >= 2000 AND year <= 2030", name="valid_year"),
        Index("idx_runner_name", "last_name", "first_name"),
        Index("idx_runner_event_year", "event", "year"),
        Index("idx_runner_team", "college_team"),
    )
    
    def __repr__(self) -> str:
        return f"<Runner(id={self.runner_id}, name='{self.first_name} {self.last_name}', event='{self.event}')>"


class Swimmer(Base):
    """
    Athletes with swimming background scraped from SwimCloud.
    
    Stores swimmer profiles and best times for matching against runners.
    Multiple time entries stored in JSONB for flexibility with different events.
    """
    __tablename__ = "swimmers"
    
    # Primary key
    swimmer_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Athlete identification (normalized for matching)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    
    # Profile data
    hometown = Column(String(200))
    birth_year = Column(Integer)
    swim_team = Column(String(200))
    
    # Swimming performance data (stored as JSONB for flexibility)
    # Format: {"200_Free_LCM": 120.45, "400_Free_LCM": 250.12, ...}
    best_times = Column(get_json_type())
    
    # Metadata
    scrape_timestamp = Column(DateTime, nullable=False, default=func.now())
    swimcloud_url = Column(String(500))  # Original profile URL
    raw_swim_json = Column(get_json_type())  # Full scraped profile data
    
    # Relationships
    matches = relationship("RunnerSwimmerMatch", back_populates="swimmer")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("birth_year IS NULL OR (birth_year >= 1990 AND birth_year <= 2010)", name="valid_birth_year"),
        Index("idx_swimmer_name", "last_name", "first_name"),
        Index("idx_swimmer_hometown", "hometown"),
        Index("idx_swimmer_birth_year", "birth_year"),
    )
    
    def __repr__(self) -> str:
        return f"<Swimmer(id={self.swimmer_id}, name='{self.first_name} {self.last_name}', team='{self.swim_team}')>"


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


class RunnerSwimmerMatch(Base):
    """
    Potential matches between runners and swimmers with scoring details.
    
    Stores fuzzy matching results including similarity scores and field-level
    match details. Supports manual review workflow with verification status.
    """
    __tablename__ = "runner_swimmer_match"
    
    # Primary key
    match_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    runner_id = Column(Integer, ForeignKey("runners.runner_id"), nullable=False)
    swimmer_id = Column(Integer, ForeignKey("swimmers.swimmer_id"), nullable=False)
    
    # Matching algorithm results
    match_score = Column(DECIMAL(5, 2), nullable=False)  # 0.00 to 100.00
    name_similarity = Column(DECIMAL(5, 2))  # Component scores for debugging
    hometown_bonus = Column(DECIMAL(5, 2))
    birth_year_bonus = Column(DECIMAL(5, 2))
    school_bonus = Column(DECIMAL(5, 2))
    
    # Match details for audit trail
    matched_on_fields = Column(get_array_type())  # ['name', 'hometown', 'birth_year']
    match_explanation = Column(Text)  # Human-readable explanation of match
    
    # Review workflow
    verification_status = Column(String(20), nullable=False, default="pending")  # "auto_verified", "manual_review", "no_match", "verified", "rejected"
    reviewer_notes = Column(Text)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    
    # Metadata
    match_timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # Relationships
    runner = relationship("Runner", back_populates="matches")
    swimmer = relationship("Swimmer", back_populates="matches")
    classifications = relationship("Classification", back_populates="match")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("match_score >= 0 AND match_score <= 100", name="valid_match_score"),
        CheckConstraint("verification_status IN ('pending', 'auto_verified', 'manual_review', 'no_match', 'verified', 'rejected')", name="valid_verification_status"),
        UniqueConstraint("runner_id", "swimmer_id", name="unique_runner_swimmer_pair"),
        Index("idx_match_score", "match_score"),
        Index("idx_match_status", "verification_status"),
        Index("idx_match_review", "verification_status", "match_score"),
    )
    
    def __repr__(self) -> str:
        return f"<RunnerSwimmerMatch(id={self.match_id}, score={self.match_score}, status='{self.verification_status}')>"


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
    match_id = Column(Integer, ForeignKey("runner_swimmer_match.match_id"), nullable=False)
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
    match = relationship("RunnerSwimmerMatch", back_populates="classifications")
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
