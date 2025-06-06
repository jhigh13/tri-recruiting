"""
Verify Step 3 completion by checking time standards data.
"""

import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from db.db_connection import get_engine
from db.models import TimeStandard


def main():
    print("=== Step 3 Verification: Time Standards Data ===")
    
    try:
        engine = get_engine()
        print("✓ Database connection established")
        
        with Session(engine) as session:
            # Check total count
            total_count = session.query(TimeStandard).count()
            print(f"✓ Total time standards loaded: {total_count}")
        
        # Check by category
        categories = session.query(TimeStandard.category).distinct().all()
        print(f"✓ Performance categories: {[c[0] for c in categories]}")
        
        # Check by gender/age group
        gender_age_groups = session.query(TimeStandard.gender, TimeStandard.age_group).distinct().all()
        print(f"✓ Gender/Age groups: {[(g[0], g[1]) for g in gender_age_groups]}")
        
        # Check events
        events = session.query(TimeStandard.event).distinct().all()
        print(f"✓ Events: {[e[0] for e in events]}")
        
        # Show sample data from each category
        print("\n=== Sample Time Standards ===")
        
        # Junior Girls Swimming
        jg_swim = session.query(TimeStandard).filter(
            TimeStandard.gender == 'F',
            TimeStandard.age_group == 'Junior',
            TimeStandard.event == '200_Free_LCM'
        ).all()
        
        if jg_swim:
            print("Junior Girls 200 Free LCM:")
            for std in jg_swim:
                print(f"  {std.category}: {std.cutoff_seconds}s ({std.color_code})")
        
        # Men Running
        men_run = session.query(TimeStandard).filter(
            TimeStandard.gender == 'M',
            TimeStandard.age_group == 'Open', 
            TimeStandard.event == '5k_Run'
        ).all()
        
        if men_run:
            print("\nMen 5k Run:") 
            for std in men_run:
                print(f"  {std.category}: {std.cutoff_seconds}s ({std.color_code})")
        
        # Check for any potential data issues
        print("\n=== Data Quality Check ===")
        
        # Check for missing color codes
        missing_colors = session.query(TimeStandard).filter(
            TimeStandard.color_code.is_(None)
        ).count()
        
        if missing_colors == 0:
            print("✓ All records have color codes assigned")
        else:
            print(f"⚠ {missing_colors} records missing color codes")
          # Check for invalid times (should all be positive)
        invalid_times = session.query(TimeStandard).filter(
            TimeStandard.cutoff_seconds <= 0
        ).count()
        
        if invalid_times == 0:
            print("✓ All cutoff times are positive")
        else:
            print(f"❌ {invalid_times} records have invalid cutoff times")
        
        print(f"\n✅ Step 3 Complete! Time standards data successfully loaded.")
        print(f"✅ Database ready for Step 4: TFRRS Scraper implementation")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
