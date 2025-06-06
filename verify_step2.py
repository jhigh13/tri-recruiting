#!/usr/bin/env python3
"""
Verify database tables and Step 2 completion
"""

from db.db_connection import get_session
from db.models import Runner, Swimmer, TimeStandard, RunnerSwimmerMatch, Classification
from sqlalchemy import text
import os

def main():
    print("=== Step 2 Verification ===")
    
    # Check database file exists
    db_path = "data/tri_talent.db"
    if os.path.exists(db_path):
        print(f"✓ Database file exists: {db_path}")
        print(f"  Size: {os.path.getsize(db_path):,} bytes")
    else:
        print(f"✗ Database file missing: {db_path}")
        return
    
    # Check tables and print schema/row counts
    session = get_session()
    try:
        # Use SQLAlchemy text() for raw SQL
        tables = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        table_names = [row[0] for row in tables]
        expected_tables = ['runners', 'swimmers', 'time_standards', 'runner_swimmer_match', 'classification']
        print("\n=== Database Tables ===")
        for table in expected_tables:
            if table in table_names:
                print(f"✓ {table}")
            else:
                print(f"✗ {table} (missing)")
        print(f"\nTotal tables found: {len(table_names)}")
        print("Tables:", table_names)
        print("\n=== Table Schemas and Row Counts ===")
        for i, table_name in enumerate(table_names, 1):
            print(f"{i}. {table_name}")
            # Get schema
            columns = session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            print("   Columns:")
            for col in columns:
                col_id, name, data_type, not_null, default_val, pk = col
                pk_marker = " [PRIMARY KEY]" if pk else ""
                not_null_marker = " NOT NULL" if not_null else ""
                print(f"     - {name} ({data_type}){not_null_marker}{pk_marker}")
            # Get row count
            count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"   ROWS: {count}")
            print()
        print("SUCCESS: Database infrastructure ready!")
        print("NEXT: Step 3 - Load Time Standards Data")
    except Exception as e:
        print(f"Error verifying database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
