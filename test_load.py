#!/usr/bin/env python3
"""Simple test to load standards"""

import pandas as pd
from db.db_connection import get_session
from db.models import TimeStandard

def test_load():
    print("Testing standards load...")
    
    # Read CSV
    df = pd.read_csv("etl/data/tri_standards.csv")
    print(f"CSV has {len(df)} rows")
    print("Columns:", df.columns.tolist())
    print("First row:", df.iloc[0].to_dict())
    
    # Check database connection
    session = get_session()
    try:
        count = session.query(TimeStandard).count()
        print(f"Current records in time_standards: {count}")
        
        # Try adding one record
        standard = TimeStandard(
            gender='F',
            age_group='Junior', 
            event='Swim 200 Free',
            category='World Leading',
            cutoff_seconds=136.0,
            color_code='#006400',
            display_order=1
        )
        session.add(standard)
        session.commit()
        
        new_count = session.query(TimeStandard).count()
        print(f"After adding test record: {new_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_load()
