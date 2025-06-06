"""
Database table creation script for the USA Triathlon Talent ID Pipeline.

This script creates all necessary database tables using SQLAlchemy models.
Works with both PostgreSQL and SQLite databases.

Usage:
    python db/create_tables.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.db_connection import get_engine, DATABASE_URL
from db.models import Base
from sqlalchemy import text


def create_tables() -> None:
    """
    Create all database tables defined in models.py.
    
    This function will:
    1. Connect to the database
    2. Create all tables if they don't exist
    3. Set up indexes and constraints
    """
    try:
        print("Connecting to database...")
        print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
        
        engine = get_engine()
        
        print("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
        
        print("Creating database tables...")
        Base.metadata.create_all(engine)
        
        print("✓ Database tables created successfully!")
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
        print("\nNext steps:")
        print("1. Load time standards: python etl/extract_standards.py")
        print("2. Load standards data: python etl/standards_loader.py")
        print("3. Start scraping: python etl/scrape_tfrrs.py")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has correct DATABASE_URL")
        print("2. Ensure virtual environment is activated")
        print("3. Verify all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)


def drop_tables() -> None:
    """
    Drop all database tables. Use with caution!
    
    This is useful for development when you need to reset the schema.
    """
    try:
        engine = get_engine()
        print("WARNING: This will delete all data!")
        confirm = input("Type 'yes' to continue: ")
        
        if confirm.lower() == 'yes':
            print("Dropping all tables...")
            Base.metadata.drop_all(engine)
            print("✓ All tables dropped successfully!")
        else:
            print("Operation cancelled.")
            
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        sys.exit(1)


def main():
    """Main entry point for database setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database setup for USA Triathlon Talent ID Pipeline")
    parser.add_argument("--drop", action="store_true", help="Drop all tables (destructive operation)")
    
    args = parser.parse_args()
    
    if args.drop:
        drop_tables()
    else:
        create_tables()


if __name__ == "__main__":
    main()
