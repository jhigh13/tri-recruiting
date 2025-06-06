#!/usr/bin/env python3
"""
Load time standards from tri_standards.csv into the time_standards table.

This script processes the tri_standards.csv file created by the user and loads
the data into the SQLite database with proper time parsing and normalization.
"""

import pandas as pd
import re
from datetime import datetime
from typing import Optional, Tuple
from db.db_connection import get_session
from db.models import TimeStandard

# Color mappings for each tier
TIER_COLORS = {
    'World Leading': '#006400',        # Dark Green
    'Internationally Ranked': '#32CD32', # Green  
    'Nationally Competitive': '#FFD700',  # Yellow
    'Development Potential': '#FF6347'    # Red
}

def parse_time_to_seconds(time_str: str) -> Optional[float]:
    """
    Convert time string to seconds.
    
    Handles formats like:
    - "2:15" -> 135.0 seconds
    - "34:00:00" -> 122400.0 seconds  
    - "4:47 / 5:15" -> 287.0 seconds (takes first time for SCY)
    
    Args:
        time_str: Time string to parse
        
    Returns:
        float: Time in seconds, or None if parsing fails
    """
    if not time_str or time_str.strip() == '':
        return None
        
    # Handle dual times (SCY / LCM) - take the first one (SCY)
    if ' / ' in time_str:
        time_str = time_str.split(' / ')[0].strip()
    
    # Remove any extra whitespace
    time_str = time_str.strip()
    
    try:
        # Handle HH:MM:SS format (for 10k times)
        if time_str.count(':') == 2:
            hours, minutes, seconds = time_str.split(':')
            return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        
        # Handle MM:SS format (most common)
        elif time_str.count(':') == 1:
            minutes, seconds = time_str.split(':')
            return int(minutes) * 60 + int(seconds)
        
        # Handle seconds only (shouldn't occur but just in case)
        else:
            return float(time_str)
            
    except (ValueError, IndexError) as e:
        print(f"Warning: Could not parse time '{time_str}': {e}")
        return None

def determine_gender(category: str) -> str:
    """
    Extract gender from category.
    
    Args:
        category: Category like "Junior Girls", "Women", "Men", etc.
        
    Returns:
        str: 'F' for female, 'M' for male
    """
    if 'Girls' in category or 'Women' in category:
        return 'F'
    elif 'Boys' in category or 'Men' in category:
        return 'M'
    else:
        return 'U'  # Unknown

def determine_age_group(category: str) -> str:
    """
    Extract age group from category.
    
    Args:
        category: Category like "Junior Girls", "Women", "Men", etc.
        
    Returns:
        str: Age group identifier
    """
    if 'Junior' in category:
        return 'Junior'
    else:
        return 'Senior'

def load_standards_from_csv(csv_path: str) -> None:
    """
    Load time standards from CSV file into database.
    
    Args:
        csv_path: Path to the CSV file
    """
    print(f"Loading time standards from: {csv_path}")
    
    # Read CSV file
    try:
        df = pd.read_csv(csv_path)
        print(f"Read {len(df)} rows from CSV")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Remove empty rows
    df = df.dropna(subset=['Category', 'Discipline', 'Event'])
    print(f"After removing empty rows: {len(df)} rows")
    
    # Get database session
    session = get_session()
    
    try:
        # Clear existing standards (for clean reload)
        session.query(TimeStandard).delete()
        session.commit()
        print("Cleared existing time standards")
        
        records_loaded = 0
        
        # Process each row
        for index, row in df.iterrows():
            category = row['Category']
            discipline = row['Discipline'] 
            event = row['Event']
            
            # Skip if essential fields are missing
            if pd.isna(category) or pd.isna(discipline) or pd.isna(event):
                continue
                
            gender = determine_gender(category)
            age_group = determine_age_group(category)
            
            # Process each tier (World Leading, Internationally Ranked, etc.)
            tier_columns = ['World Leading', 'Internationally Ranked', 
                          'Nationally Competitive', 'Development Potential']
            
            for display_order, tier in enumerate(tier_columns, 1):
                time_str = str(row[tier]) if not pd.isna(row[tier]) else None
                
                if time_str and time_str != 'nan':
                    cutoff_seconds = parse_time_to_seconds(time_str)
                    
                    if cutoff_seconds is not None:
                        # Create TimeStandard record
                        standard = TimeStandard(
                            gender=gender,
                            age_group=age_group,
                            event=f"{discipline} {event}",
                            category=tier,
                            cutoff_seconds=cutoff_seconds,
                            color_code=TIER_COLORS[tier],
                            display_order=display_order
                        )
                        
                        session.add(standard)
                        records_loaded += 1
                        
                        # Debug print for first few records
                        if records_loaded <= 5:
                            print(f"  Added: {gender} {age_group} {discipline} {event} - {tier}: {time_str} ({cutoff_seconds}s)")
        
        # Commit all changes
        session.commit()
        print(f"\nSuccessfully loaded {records_loaded} time standard records!")
        
        # Verify the load
        total_records = session.query(TimeStandard).count()
        print(f"Total records in time_standards table: {total_records}")
        
        # Show sample data
        print("\nSample loaded records:")
        samples = session.query(TimeStandard).limit(10).all()
        for standard in samples:
            print(f"  {standard.gender} {standard.age_group} {standard.event} - {standard.category}: {standard.cutoff_seconds}s")
        
    except Exception as e:
        session.rollback()
        print(f"Error loading standards: {e}")
        raise
    finally:
        session.close()

def main():
    """Main function to load time standards."""
    csv_path = "etl/data/tri_standards.csv"
    load_standards_from_csv(csv_path)
    print("\nStep 3 complete: Time standards loaded successfully!")

if __name__ == "__main__":
    main()
