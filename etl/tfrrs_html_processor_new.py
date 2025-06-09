"""
TFRRS Data Processor - Updated to handle actual TFRRS HTML structure.
"""
import argparse
import logging
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

# Local imports
sys.path.append(str(Path(__file__).parent.parent))
from db.db_connection import get_engine
from db.models import Runner

# Ensure console can handle Unicode
import io, sys as _sys
_sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8', errors='replace')
_sys.stderr = io.TextIOWrapper(_sys.stderr.buffer, encoding='utf-8', errors='replace')
# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tfrrs_processor.log'),
        logging.StreamHandler()
    ]
)

# Target events for both outdoor and indoor races (distance events relevant to triathlon)
TARGET_EVENTS = {
    '800': ['800', '800m', '800 meters'],
    'mile': ['mile', 'the mile', '1 mile', '1mile'],
    '3000': ['3000', '3000m', '3000 meters'],
    '5000': ['5000', '5000m', '5000 meters', '5k'],
    '1500': ['1500', '1500m', '1500 meters'],
    '10000': ['10000', '10000m', '10000 meters', '10k', '10,000', '10,000 meters'],
    '3000steeplechase': ['steeplechase', 'steeple']
}

# Maximum athletes to store per event
MAX_ATHLETES_PER_EVENT = 500


def parse_time_to_seconds(time_str: str) -> Optional[Decimal]:
    """Convert a performance mark into total seconds."""
    if not time_str or not time_str.strip():
        return None
        
    # Clean the string - remove wind readings and other annotations
    time_match = re.search(r'(\d+:)?\d+\.\d+', time_str.strip())
    if not time_match:
        time_match = re.search(r'(\d+:)?\d+', time_str.strip())
    
    if not time_match:
        return None
        
    cleaned = time_match.group(0)
    
    try:
        if ':' in cleaned:
            # Format like "1:45.23" 
            parts = cleaned.split(':')
            if len(parts) == 2:
                mins = int(parts[0])
                secs = float(parts[1])
                total = mins * 60 + secs
                return Decimal(str(total)).quantize(Decimal('0.01'))
        else:
            # Format like "45.23" (seconds only)
            total = float(cleaned)
            return Decimal(str(total)).quantize(Decimal('0.01'))
    except (ValueError, Exception) as e:
        logger.debug(f"Could not parse time '{time_str}': {e}")
        return None
    
    return None


def is_target_event(event_name: str) -> bool:
    """Check if an event is one of our target outdoor distance events."""
    event_lower = event_name.lower()
    
    for target_key, variations in TARGET_EVENTS.items():
        for variation in variations:
            if variation.lower() in event_lower:
                return True
    
    return False


def normalize_event_name(event_name: str) -> str:
    """Normalize event names to standard format."""
    event_lower = event_name.lower()
    
    # Check each target event category (indoor and outdoor)
    if any(var in event_lower for var in TARGET_EVENTS['800']):
        return '800m'
    elif any(var in event_lower for var in TARGET_EVENTS['mile']):
        return 'mile'
    elif any(var in event_lower for var in TARGET_EVENTS['3000']):
        return '3000m'
    elif any(var in event_lower for var in TARGET_EVENTS['5000']):
        return '5000m'
    elif any(var in event_lower for var in TARGET_EVENTS['1500']):
        return '1500m'
    elif any(var in event_lower for var in TARGET_EVENTS['10000']):
        return '10000m'
    elif any(var in event_lower for var in TARGET_EVENTS['3000steeplechase']):
        return '3000m_steeplechase'
    return event_name


def extract_event_info_from_context(performance_list_div) -> Dict[str, str]:
    """Extract event name and gender from the context around a performance list."""
    # Look for the custom-table-title div that should be before this performance list
    current = performance_list_div.parent
    while current:
        title_div = current.find('div', class_='custom-table-title')
        if title_div:
            h3_tag = title_div.find('h3')
            if h3_tag:
                title_text = h3_tag.get_text().strip()
                
                # Extract event name - handle formats like "10,000 Meters", "1500 Meters", etc.
                event_match = re.search(r'(\d{1,2},?\d{3}(?:\.\d+)?\s*(?:Meters|Meter|m|Miles?|Mile))', title_text, re.IGNORECASE)
                if not event_match:
                    # Try for shorter distances like "800 Meters"
                    event_match = re.search(r'(\d+(?:\.\d+)?\s*(?:Meters|Meter|m|Miles?|Mile))', title_text, re.IGNORECASE)
                
                if event_match:
                    event_name = event_match.group(1).replace(' ', '').lower()
                    # Normalize event names - remove commas for consistency
                    event_name = event_name.replace(',', '')
                    if 'meter' in event_name or 'm' in event_name:
                        event_name = re.sub(r'meters?|m', 'm', event_name)
                else:
                    # Fallback - use the first part before parentheses
                    event_name = title_text.split('(')[0].strip()
                
                # Extract gender
                gender = 'M'  # Default
                if '(Men)' in title_text or '(men)' in title_text:
                    gender = 'M'
                elif '(Women)' in title_text or '(women)' in title_text:
                    gender = 'F'
                
                return {'event': event_name, 'gender': gender}
        
        current = current.parent
    
    return {'event': 'Unknown', 'gender': 'M'}


def extract_athlete_from_performance_row(row_div, event_name: str, gender: str) -> Optional[Dict[str, str]]:
    """Extract athlete data from a performance-list-row div."""
    try:
        # Extract place/rank
        place_div = row_div.find('div', class_='col-place')
        rank = 1
        if place_div:
            place_text = place_div.get_text().strip()
            rank_match = re.search(r'\d+', place_text)
            if rank_match:
                rank = int(rank_match.group())

        # Extract athlete name
        athlete_div = row_div.find('div', class_='col-athlete')
        if not athlete_div:
            return None
            
        athlete_link = athlete_div.find('a')
        if athlete_link:
            name_text = athlete_link.get_text().strip()
        else:
            name_text = athlete_div.get_text().strip()
        
        if not name_text or len(name_text) < 3:
            return None
            
        # Parse name (format is usually "Last, First")
        if ',' in name_text:
            name_parts = name_text.split(',', 1)
            last_name = name_parts[0].strip()
            first_name = name_parts[1].strip()
        else:
            # Handle cases where name might be "First Last"
            name_parts = name_text.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = name_text
                last_name = ""
        
        # Extract year/class
        year_div = row_div.find('div', class_='col-narrow', attrs={'data-label': 'Year'})
        year_text = ""
        if year_div:
            year_text = year_div.get_text().strip()
        
        # Extract team/school
        team_div = row_div.find('div', class_='col-team')
        school = "Unknown School"
        if team_div:
            team_link = team_div.find('a')
            if team_link:
                school = team_link.get_text().strip()
            else:
                school = team_div.get_text().strip()
        
        # Extract performance time
        time_div = row_div.find('div', class_='col-narrow', attrs={'data-label': 'Time'})
        if not time_div:
            return None
            
        time_link = time_div.find('a')
        if time_link:
            time_text = time_link.get_text().strip()
        else:
            time_text = time_div.get_text().strip()
        
        performance_time = parse_time_to_seconds(time_text)
        if performance_time is None or performance_time <= 0:
            return None
        
        # Extract meet info (optional)
        meet_div = row_div.find('div', class_='col-meet')
        meet_name = ""
        if meet_div:
            meet_link = meet_div.find('a')
            if meet_link:
                meet_name = meet_link.get_text().strip()
            else:
                meet_name = meet_div.get_text().strip()
        
        # Extract meet date (optional)
        date_div = row_div.find('div', class_='col-narrow', attrs={'data-label': 'Meet Date'})
        meet_date = ""
        if date_div:
            meet_date = date_div.get_text().strip()
        
        athlete_data = {
            'rank': rank,
            'first_name': first_name.lower(),
            'last_name': last_name.lower(),
            'college_team': school,
            'event': event_name,
            'performance_time': performance_time,
            'year_scraped': datetime.now().year,
            'gender': gender,
            'raw_performance': time_text,
            'class_year': year_text,
            'meet_name': meet_name,
            'meet_date': meet_date,
            'scrape_timestamp': datetime.now()
        }
        
        return athlete_data
        
    except Exception as e:
        logger.debug(f"Error parsing performance row: {e}")
        return None


def process_html_file(file_path: str) -> List[Dict[str, str]]:
    """
    Process a TFRRS HTML file and extract athlete data.
    
    Args:
        file_path: Path to the HTML file
        
    Returns:
        List of athlete dictionaries
    """
    logger.info(f"Processing HTML file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    athletes = []
    event_counts = {}
    
    # Find all performance-list sections
    performance_lists = soup.find_all('div', class_='performance-list')
    logger.info(f"Found {len(performance_lists)} performance lists")
    
    for list_div in performance_lists:
        # Extract event and gender info from the context
        event_info = extract_event_info_from_context(list_div)
        raw_event_name = event_info.get('event', 'Unknown')
        gender = event_info.get('gender', 'M')
        
        # Check if this is a target event
        if not is_target_event(raw_event_name):
            logger.info(f"Skipping non-target event: {raw_event_name}")
            continue
        
        # Normalize the event name
        event_name = normalize_event_name(raw_event_name)
        event_key = f"{event_name}_{gender}"
        
        logger.info(f"Processing target event: {event_name}, gender: {gender}")
        
        # Initialize counter for this event
        if event_key not in event_counts:
            event_counts[event_key] = 0
        
        # Find all performance rows in this list
        rows = list_div.find_all('div', class_='performance-list-row')
        logger.info(f"Found {len(rows)} athletes in this event")
        
        for row in rows:
            # Check if we've already stored enough athletes for this event
            if event_counts[event_key] >= MAX_ATHLETES_PER_EVENT:
                logger.info(f"Reached maximum of {MAX_ATHLETES_PER_EVENT} athletes for {event_key}")
                break
                
            athlete_data = extract_athlete_from_performance_row(row, event_name, gender)
            if athlete_data:
                athletes.append(athlete_data)
                event_counts[event_key] += 1
                logger.debug(f"Parsed: {athlete_data['rank']}. {athlete_data['first_name']} {athlete_data['last_name']} ({athlete_data['college_team']}) - {athlete_data['raw_performance']}")
    
    # Remove duplicates based on name and school combination
    unique_athletes = {}
    for athlete in athletes:
        key = f"{athlete['first_name']}_{athlete['last_name']}_{athlete['college_team']}"
        if key not in unique_athletes:
            unique_athletes[key] = athlete
    
    logger.info(f"Parsed {len(unique_athletes)} unique athletes from HTML content")
    
    # Log counts by event
    final_counts = {}
    for athlete in unique_athletes.values():
        event_key = f"{athlete['event']}_{athlete['gender']}"
        final_counts[event_key] = final_counts.get(event_key, 0) + 1
    
    for event_key, count in final_counts.items():
        logger.info(f"Event {event_key}: {count} athletes")
    
    return list(unique_athletes.values())


def store_athletes(athletes: List[Dict]) -> None:
    """Store athletes in the database."""
    if not athletes:
        logger.info("No athletes to store")
        return
        
    engine = get_engine()
    try:
        with Session(engine) as session:
            stored_count = 0
            for data in athletes:
                runner = Runner(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    college_team=data['college_team'],
                    event=data['event'],
                    performance_time=data['performance_time'],
                    year=data['year_scraped'],
                    gender=data['gender'],
                    birth_year=None,
                    scrape_timestamp=data['scrape_timestamp'],
                    raw_data={
                        'raw_performance': data['raw_performance'],
                        'class_year': data.get('class_year', ''),
                        'meet_name': data.get('meet_name', ''),
                        'meet_date': data.get('meet_date', ''),
                        'scrape_source': 'TFRRS_HTML'
                    }
                )
                session.merge(runner)
                stored_count += 1
                
            session.commit()
            logger.info(f"Successfully stored {stored_count} athletes in database")
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


def main():
    """Main processing function."""
    parser = argparse.ArgumentParser(description='TFRRS HTML Content Processor')
    parser.add_argument('--file', help='HTML file to process (relative to etl/data/)', required=True)
    args = parser.parse_args()

    # Get filename and ensure .html extension
    file_path = args.file
    if not file_path.lower().endswith('.html'):
        file_path = f"{file_path}.html"
    # Always look for files in etl/data/ unless an absolute path is given
    if not Path(file_path).is_absolute():
        file_path = str(Path(__file__).parent / 'data' / file_path)

    athletes = process_html_file(file_path)
    if athletes:
        store_athletes(athletes)
        print(f"Stored {len(athletes)} athletes from {file_path}.")
    else:
        print(f"No athletes found in {file_path}.")


if __name__ == "__main__":
    main()
