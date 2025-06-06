"""
Load USA Triathlon time standards from CSV into the database.

This script processes the tri_standards.csv file and loads performance benchmarks
into the time_standards table. Handles various time formats and ensures data
integrity through validation and normalization.

Time Format Handling:
- Swim times: "2:16 / 2:00" (SCY / LCM format)
- Run times: "2:15" (minutes:seconds) or "34:00:00" (hours:minutes:seconds)
- Converts all times to total seconds for database storage

Usage:
    python etl/standards_loader.py
"""

import csv
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from db.db_connection import get_engine
from db.models import TimeStandard


# Constants for data consistency
MATCH_THRESHOLD = 90
COLOR_MAPPING = {
    "World Leading": "Dark_Green",
    "Internationally Ranked": "Green", 
    "Nationally Competitive": "Yellow",
    "Development Potential": "Red"
}

GENDER_MAPPING = {
    "Junior Girls": "F",
    "Junior Boys": "M", 
    "Women": "F",
    "Men": "M"
}

AGE_GROUP_MAPPING = {
    "Junior Girls": "Junior",
    "Junior Boys": "Junior",
    "Women": "Open", 
    "Men": "Open"
}


def parse_time_to_seconds(time_str: str) -> Optional[Decimal]:
    """
    Convert various time formats to total seconds.
    
    Handles:
    - Swimming: "2:16 / 2:00" (takes LCM time - second value)
    - Running: "2:15" (mm:ss) or "34:00:00" (hh:mm:ss)
    - Edge cases: empty strings, malformed data
    
    Args:
        time_str: Time string from CSV
        
    Returns:
        Decimal seconds or None if parsing fails
    """
    if not time_str or time_str.strip() == "":
        return None
        
    time_str = time_str.strip()
    
    # Handle swimming format "2:16 / 2:00" - use LCM time (second value)
    if " / " in time_str:
        parts = time_str.split(" / ")
        if len(parts) == 2:
            time_str = parts[1].strip()  # Use LCM time
    
    # Remove any extra whitespace
    time_str = time_str.strip()
    
    # Handle hours:minutes:seconds format (e.g., "34:00:00")
    if time_str.count(":") == 2:
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return Decimal(str(total_seconds))
        except ValueError:
            print(f"Warning: Could not parse time format (HH:MM:SS): {time_str}")
            return None
    
    # Handle minutes:seconds format (e.g., "2:15")
    elif time_str.count(":") == 1:
        try:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])  # Allow decimal seconds
            total_seconds = minutes * 60 + seconds
            return Decimal(str(total_seconds)).quantize(Decimal('0.01'))
        except ValueError:
            print(f"Warning: Could not parse time format (MM:SS): {time_str}")
            return None
    
    # Handle seconds only format
    else:
        try:
            return Decimal(str(float(time_str))).quantize(Decimal('0.01'))
        except ValueError:
            print(f"Warning: Could not parse time format (seconds): {time_str}")
            return None


def normalize_event_name(event: str, discipline: str) -> str:
    """
    Normalize event names for consistent database storage.
    
    Args:
        event: Raw event name from CSV
        discipline: "Swim" or "Run"
        
    Returns:
        Normalized event name (e.g., "200_Free_LCM", "5k_Run")
    """
    event = event.strip()
    
    if discipline == "Swim":
        # Handle swim events
        if "200 Free" in event:
            return "200_Free_LCM"
        elif "400 / 500 Free" in event:
            return "400_500_Free_LCM"
        elif "800 / 1000 Free" in event:
            return "800_1000_Free_LCM"
        elif "1500 / 1650 Free" in event:
            return "1500_1650_Free_LCM"
    
    elif discipline == "Run":
        # Handle running events
        if event == "800":
            return "800m_Run"
        elif event == "1500":
            return "1500m_Run"
        elif event == "Mile":
            return "Mile_Run"
        elif event == "3000":
            return "3000m_Run"
        elif event == "5k":
            return "5k_Run"
        elif event == "10k":
            return "10k_Run"
    
    # Fallback: return original with underscores
    return event.replace(" ", "_").replace("/", "_")


def load_standards_from_csv(csv_path: Path) -> List[TimeStandard]:
    """
    Parse CSV file and create TimeStandard objects.
    
    Args:
        csv_path: Path to tri_standards.csv file
        
    Returns:
        List of TimeStandard objects ready for database insertion    """
    standards = []
      try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                # Skip empty rows - check if any non-empty values exist
                if not any(value.strip() for value in row.values() if value):
                    continue
                
                category = row['Category'].strip()
                discipline = row['Discipline'].strip()
                event = row['Event'].strip()
                
                # Skip if essential fields are missing
                if not category or not discipline or not event:
                    continue
                
                # Extract gender and age group
                gender = GENDER_MAPPING.get(category)
                age_group = AGE_GROUP_MAPPING.get(category)
                
                if not gender or not age_group:
                    print(f"Warning: Unknown category '{category}' on row {row_num}")
                    continue
                
                # Normalize event name
                normalized_event = normalize_event_name(event, discipline)
                
                # Process each performance tier
                tier_columns = [
                    "World Leading",
                    "Internationally Ranked", 
                    "Nationally Competitive",
                    "Development Potential"
                ]
                
                for tier in tier_columns:
                    time_value = row.get(tier, "").strip()
                    if not time_value:
                        continue
                    
                    cutoff_seconds = parse_time_to_seconds(time_value)
                    if cutoff_seconds is None:
                        print(f"Warning: Could not parse time '{time_value}' for {category} {normalized_event} {tier} on row {row_num}")
                        continue
                    
                    # Create TimeStandard object
                    standard = TimeStandard(
                        gender=gender,
                        age_group=age_group,
                        event=normalized_event,
                        category=tier,
                        cutoff_seconds=cutoff_seconds,
                        color_code=COLOR_MAPPING.get(tier),
                        display_order=len(standards)
                    )
                    
                    standards.append(standard)
    
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_path}")
        return []
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []
    
    return standards


def clear_existing_standards(session: Session) -> None:
    """
    Remove all existing time standards from the database.
    
    Args:
        session: SQLAlchemy database session
    """
    try:
        deleted_count = session.query(TimeStandard).delete()
        session.commit()
        print(f"Cleared {deleted_count} existing time standards")
    except Exception as e:
        session.rollback()
        print(f"Error clearing existing standards: {e}")
        raise


def load_standards_to_database(standards: List[TimeStandard]) -> None:
    """
    Load time standards into the database with proper error handling.
    
    Args:
        standards: List of TimeStandard objects to insert
    """
    engine = get_engine()
    
    with Session(engine) as session:
        try:
            # Clear existing data
            clear_existing_standards(session)
            
            # Insert new standards
            for standard in standards:
                session.add(standard)
            
            session.commit()
            print(f"Successfully loaded {len(standards)} time standards")
            
        except Exception as e:
            session.rollback()
            print(f"Error loading standards to database: {e}")
            raise


def validate_loaded_data(session: Session) -> Dict[str, int]:
    """
    Validate the loaded data and return summary statistics.
    
    Args:
        session: SQLAlchemy database session
        
    Returns:
        Dictionary with validation statistics
    """
    stats = {}
    
    # Count total records
    stats['total_records'] = session.query(TimeStandard).count()
    
    # Count by category
    categories = session.query(TimeStandard.category).distinct().all()
    stats['categories'] = len(categories)
    
    # Count by gender
    genders = session.query(TimeStandard.gender).distinct().all()
    stats['genders'] = len(genders)
    
    # Count by event
    events = session.query(TimeStandard.event).distinct().all()
    stats['events'] = len(events)
    
    return stats


def main() -> None:
    """
    Main function to load time standards from CSV to database.
    """
    print("USA Triathlon Time Standards Loader")
    print("=" * 40)
    
    # Locate CSV file
    csv_path = Path(__file__).parent / "data" / "tri_standards.csv"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    print(f"Loading time standards from: {csv_path}")
    
    # Parse CSV data
    standards = load_standards_from_csv(csv_path)
    
    if not standards:
        print("No valid time standards found in CSV file")
        return
    
    print(f"Parsed {len(standards)} time standards from CSV")
    
    # Load to database
    try:
        load_standards_to_database(standards)
        
        # Validate results
        engine = get_engine()
        with Session(engine) as session:
            stats = validate_loaded_data(session)
            
            print("\nLoad Summary:")
            print(f"  Total records: {stats['total_records']}")
            print(f"  Performance categories: {stats['categories']}")
            print(f"  Genders: {stats['genders']}")
            print(f"  Events: {stats['events']}")
            
            # Show sample records
            print("\nSample loaded records:")
            sample_records = session.query(TimeStandard).limit(5).all()
            for record in sample_records:
                print(f"  {record.gender} {record.age_group} {record.event} {record.category}: {record.cutoff_seconds}s")
        
        print("\n✅ Time standards loaded successfully!")
        
    except Exception as e:
        print(f"\n❌ Failed to load time standards: {e}")


if __name__ == "__main__":
    main()