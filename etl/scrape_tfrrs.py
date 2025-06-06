"""
TFRRS Scraper Module for NCAA Division I Track & Field Results.

This module scrapes top 500 athletes per event from TFRRS (Track & Field Results 
Reporting System) for the past 5 years, normalizes performance times, and stores
data in the runners table for matching against swimmers.

Key Features:
- Configurable event mapping via YAML
- Robust error handling and rate limiting  
- Time normalization to seconds with validation
- Duplicate detection and upsert logic
- Progress tracking and logging

Usage:
    python etl/scrape_tfrrs.py [--year 2025] [--season outdoor] [--event 800m]
"""

import argparse
import logging
import re
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import requests
import yaml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from db.db_connection import get_engine
from db.models import Runner


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tfrrs_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TFRRSScraper:
    """
    TFRRS web scraper for NCAA Division I track and field results.
    
    Handles event configuration, URL construction, HTML parsing,
    time normalization, and database storage with robust error handling.
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize scraper with configuration.
        
        Args:
            config_path: Path to events.yaml configuration file
        """
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'USA-Triathlon-TalentID-Pipeline/1.0 (Educational Research)'
        })
        
        # Scraping statistics
        self.stats = {
            'requests_made': 0,
            'athletes_scraped': 0,
            'athletes_stored': 0,
            'errors': 0
        }
    
    def _load_config(self, config_path: Path) -> Dict:
        """Load YAML configuration file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise
    
    def _construct_url(self, year: int, season: str, event_config: Dict) -> str:
        """
        Construct TFRRS URL for specific year/season/event.
        
        Args:
            year: Competition year (e.g., 2025)
            season: 'outdoor' or 'indoor'
            event_config: Event configuration from YAML
            
        Returns:
            Complete TFRRS URL
        """
        pattern = self.config['url_patterns'][season]
        list_id = self.config[f'list_id_{season}']
        
        url = pattern.format(
            base_url=self.config['base_url'],
            list_id=list_id,
            year=year,
            event_id=event_config['event_id']
        )
        
        return url
    
    def _parse_time_to_seconds(self, time_str: str) -> Optional[Decimal]:
        """
        Convert track performance time to total seconds.
        
        Handles formats:
        - "1:48.23" (minutes:seconds.hundredths)
        - "2:01" (minutes:seconds)
        - "8:15.45" (minutes:seconds.hundredths for longer events)
        - "28:45.67" (minutes:seconds.hundredths for very long events)
        
        Args:
            time_str: Performance time string from TFRRS
            
        Returns:
            Decimal seconds or None if parsing fails
        """
        if not time_str or time_str.strip() == "":
            return None
        
        # Clean the time string
        time_str = time_str.strip().replace(',', '')
        
        # Handle minutes:seconds.hundredths format
        if ':' in time_str:
            try:
                # Split on colon
                parts = time_str.split(':')
                if len(parts) != 2:
                    logger.warning(f"Unexpected time format: {time_str}")
                    return None
                
                minutes = int(parts[0])
                seconds_part = float(parts[1])
                
                total_seconds = minutes * 60 + seconds_part
                return Decimal(str(total_seconds)).quantize(Decimal('0.01'))
                
            except (ValueError, decimal.InvalidOperation) as e:
                logger.warning(f"Could not parse time '{time_str}': {e}")
                return None
        
        # Handle seconds-only format (rare but possible)
        else:
            try:
                seconds = float(time_str)
                return Decimal(str(seconds)).quantize(Decimal('0.01'))
            except (ValueError, decimal.InvalidOperation) as e:
                logger.warning(f"Could not parse time '{time_str}': {e}")
                return None
    
    def _parse_athlete_name(self, name_element) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract first and last name from athlete name element.
        
        Args:
            name_element: BeautifulSoup element containing athlete name
            
        Returns:
            Tuple of (first_name, last_name) or (None, None) if parsing fails
        """
        if not name_element:
            return None, None
        
        # Get text content and clean it
        full_name = name_element.get_text(strip=True)
        if not full_name:
            return None, None
        
        # Split name (assume "First Last" or "First Middle Last" format)
        name_parts = full_name.split()
        if len(name_parts) < 2:
            logger.warning(f"Incomplete name: {full_name}")
            return None, None
        
        # Take first part as first name, join rest as last name
        first_name = name_parts[0].strip()
        last_name = ' '.join(name_parts[1:]).strip()
        
        # Normalize for consistent matching
        first_name = first_name.lower().replace('.', '').replace(',', '')
        last_name = last_name.lower().replace('.', '').replace(',', '')
        
        return first_name, last_name
    
    def _validate_performance_time(self, time_seconds: Decimal, event_config: Dict) -> bool:
        """
        Validate performance time against reasonable bounds.
        
        Args:
            time_seconds: Performance time in seconds
            event_config: Event configuration with min/max bounds
            
        Returns:
            True if time is within reasonable bounds
        """
        min_time = event_config.get('min_time_seconds', 0)
        max_time = event_config.get('max_time_seconds', 10000)
        
        return min_time <= time_seconds <= max_time
    
    def _scrape_event_page(self, url: str, event_name: str, year: int, 
                          event_config: Dict) -> List[Dict]:
        """
        Scrape single event page and extract athlete data.
        
        Args:
            url: TFRRS URL to scrape
            event_name: Display name for event
            year: Competition year
            event_config: Event configuration
            
        Returns:
            List of athlete dictionaries
        """
        athletes = []
        
        try:
            # Respect rate limiting
            time.sleep(self.config['scraping']['request_delay_seconds'])
            
            # Make request
            response = self.session.get(
                url, 
                timeout=self.config['scraping']['timeout_seconds']
            )
            response.raise_for_status()
            self.stats['requests_made'] += 1
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
              # Find results table
            table = soup.select_one(self.config['selectors']['results_table'])
            if not table:
                logger.info(f"No results table found with BeautifulSoup, trying Selenium for {url}")
                
                # Try with Selenium for JavaScript-rendered content
                soup = self._get_page_with_selenium(url)
                if soup:
                    table = soup.select_one(self.config['selectors']['results_table'])
                
                if not table:
                    logger.warning(f"No results table found even with Selenium at {url}")
                    return athletes
            
            # Parse athlete rows
            rows = table.select(self.config['selectors']['result_rows'])
            max_athletes = self.config['scraping']['max_athletes_per_event']
            
            for i, row in enumerate(rows[:max_athletes]):
                try:
                    athlete_data = self._parse_athlete_row(row, event_name, year, event_config)
                    if athlete_data:
                        athletes.append(athlete_data)
                        self.stats['athletes_scraped'] += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing row {i} from {url}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            logger.info(f"Scraped {len(athletes)} athletes from {url}")
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            self.stats['errors'] += 1
        
        return athletes
    
    def _parse_athlete_row(self, row, event_name: str, year: int, 
                          event_config: Dict) -> Optional[Dict]:
        """
        Parse individual athlete row from results table.
        
        Args:
            row: BeautifulSoup row element
            event_name: Display name for event
            year: Competition year  
            event_config: Event configuration
            
        Returns:
            Athlete data dictionary or None if parsing fails
        """
        try:
            # Extract fields using CSS selectors
            selectors = self.config['selectors']
            
            # Athlete name and link
            name_element = row.select_one(selectors['athlete_name'])
            first_name, last_name = self._parse_athlete_name(name_element)
            
            if not first_name or not last_name:
                return None
            
            # School/team
            school_element = row.select_one(selectors['school'])
            school = school_element.get_text(strip=True) if school_element else ""
            
            # Performance time
            perf_element = row.select_one(selectors['performance'])
            perf_text = perf_element.get_text(strip=True) if perf_element else ""
            
            performance_seconds = self._parse_time_to_seconds(perf_text)
            if not performance_seconds:
                logger.warning(f"Could not parse performance time: {perf_text}")
                return None
            
            # Validate performance time
            if not self._validate_performance_time(performance_seconds, event_config):
                logger.warning(f"Performance time {performance_seconds}s outside valid range for {event_name}")
                return None
            
            # Year (competition year, not class year necessarily)
            year_element = row.select_one(selectors['year'])
            class_year = year_element.get_text(strip=True) if year_element else ""
            
            # Try to extract numeric year
            class_year_int = None
            if class_year:
                year_match = re.search(r'\d{4}', class_year)
                if year_match:
                    class_year_int = int(year_match.group())
            
            # Infer gender from event name (TFRRS lists are typically gender-specific)
            # This is a heuristic - in practice you might determine from URL patterns
            gender = "M"  # Default assumption - would need URL analysis to determine
            
            return {
                'first_name': first_name,
                'last_name': last_name,
                'college_team': school,
                'event': event_name,
                'performance_time': performance_seconds,
                'year': year,
                'gender': gender,
                'class_year': class_year_int,
                'raw_performance': perf_text,
                'scrape_timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.warning(f"Error parsing athlete row: {e}")
            return None
    
    def _store_athletes(self, athletes: List[Dict]) -> None:
        """
        Store athlete data in database using upsert logic.
        
        Args:
            athletes: List of athlete dictionaries to store
        """
        if not athletes:
            return
        
        engine = get_engine()
        
        with Session(engine) as session:
            try:
                for athlete_data in athletes:
                    # Create Runner object
                    runner = Runner(
                        first_name=athlete_data['first_name'],
                        last_name=athlete_data['last_name'],
                        college_team=athlete_data['college_team'],
                        event=athlete_data['event'],
                        performance_time=athlete_data['performance_time'],
                        year=athlete_data['year'],
                        gender=athlete_data['gender'],
                        birth_year=athlete_data.get('class_year'),
                        scrape_timestamp=athlete_data['scrape_timestamp'],
                        raw_data={
                            'raw_performance': athlete_data.get('raw_performance'),
                            'scrape_source': 'TFRRS'
                        }
                    )
                    
                    # Use merge for upsert behavior
                    session.merge(runner)
                    self.stats['athletes_stored'] += 1
                
                session.commit()
                logger.info(f"Stored {len(athletes)} athletes in database")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Database error storing athletes: {e}")
                self.stats['errors'] += 1
                raise
    
    def scrape_events(self, years: Optional[List[int]] = None, 
                     seasons: Optional[List[str]] = None,
                     events: Optional[List[str]] = None) -> None:
        """
        Main scraping method to process events across years and seasons.
        
        Args:
            years: List of years to scrape (default: from config)
            seasons: List of seasons to scrape (default: ['outdoor', 'indoor'])
            events: List of events to scrape (default: all from config)
        """
        # Set defaults
        if years is None:
            years = self.config['years_to_scrape']
        if seasons is None:
            seasons = ['outdoor', 'indoor']
        if events is None:
            events = []
        
        logger.info(f"Starting TFRRS scraping for years {years}, seasons {seasons}")
        
        for year in years:
            for season in seasons:
                season_events = self.config[f'{season}_events']
                
                # Filter events if specified
                if events:
                    season_events = {k: v for k, v in season_events.items() if k in events}
                
                for event_key, event_config in season_events.items():
                    try:
                        logger.info(f"Scraping {year} {season} {event_key}")
                        
                        # Construct URL
                        url = self._construct_url(year, season, event_config)
                        
                        # Scrape event page
                        athletes = self._scrape_event_page(
                            url, 
                            event_config['display_name'], 
                            year, 
                            event_config
                        )
                        
                        # Store in database
                        if athletes:
                            self._store_athletes(athletes)
                        
                    except Exception as e:
                        logger.error(f"Error scraping {year} {season} {event_key}: {e}")
                        self.stats['errors'] += 1
                        continue
        
        # Print final statistics
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print scraping summary statistics."""
        logger.info("=== TFRRS Scraping Summary ===")
        logger.info(f"Requests made: {self.stats['requests_made']}")
        logger.info(f"Athletes scraped: {self.stats['athletes_scraped']}")
        logger.info(f"Athletes stored: {self.stats['athletes_stored']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        
        if self.stats['requests_made'] > 0:
            success_rate = (self.stats['athletes_scraped'] / 
                          (self.stats['requests_made'] * 500)) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
    
    def _get_page_with_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """
        Use Selenium to get JavaScript-rendered page content.
        
        Args:
            url: URL to fetch with Selenium
            
        Returns:
            BeautifulSoup object of rendered page or None if failed
        """
        driver = None
        try:
            # Setup Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"--user-agent={self.session.headers['User-Agent']}")
            
            # Initialize webdriver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Navigate to page
            driver.get(url)
            
            # Wait for page to load - look for common result table indicators
            wait = WebDriverWait(driver, 10)
            
            # Try multiple selectors that might indicate page loaded
            selectors_to_wait = [
                'table',
                '.tablesaw',
                'tbody tr',
                '.results',
                '#results'
            ]
            
            page_loaded = False
            for selector in selectors_to_wait:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    page_loaded = True
                    break
                except:
                    continue
            
            if not page_loaded:
                # Wait a bit more for dynamic content
                time.sleep(3)
            
            # Get page source and parse with BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            return soup
            
        except Exception as e:
            logger.warning(f"Selenium failed for {url}: {e}")
            return None
            
        finally:
            if driver:
                driver.quit()

    # ...existing code...
def main():
    """
    Main function with command-line argument parsing.
    """
    parser = argparse.ArgumentParser(description='Scrape TFRRS track results')
    parser.add_argument('--year', type=int, help='Specific year to scrape')
    parser.add_argument('--season', choices=['outdoor', 'indoor'], 
                       help='Specific season to scrape')
    parser.add_argument('--event', help='Specific event to scrape')
    parser.add_argument('--config', default='config/events.yaml',
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Setup logging directory
    Path('logs').mkdir(exist_ok=True)
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return
    
    # Initialize scraper
    scraper = TFRRSScraper(config_path)
    
    # Determine scraping parameters
    years = [args.year] if args.year else None
    seasons = [args.season] if args.season else None
    events = [args.event] if args.event else None
    
    # Run scraping
    try:
        scraper.scrape_events(years=years, seasons=seasons, events=events)
        logger.info("TFRRS scraping completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error("Scraping failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
