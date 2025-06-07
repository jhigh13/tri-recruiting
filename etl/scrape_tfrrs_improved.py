"""
Improved TFRRS Scraper with anti-bot countermeasures and correct HTML parsing.
"""
import argparse
import logging
import re
import sys
import time
import random
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional

import requests
import requests_cache
import yaml
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Local imports
sys.path.append(str(Path(__file__).parent.parent))
from db.db_connection import get_engine
from db.models import Runner

# Configure cache with longer expiry
requests_cache.install_cache('tfrrs_cache', expire_after=3600)  # 1 hour

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tfrrs_scraper.log'),
        logging.StreamHandler()
    ]
)

# Constants for anti-bot evasion
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

MATCH_THRESHOLD = 90


def _get_random_headers() -> Dict[str, str]:
    """Generate randomized headers to avoid detection."""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }


def _parse_time_to_seconds(time_str: str) -> Optional[Decimal]:
    """Convert a performance mark into total seconds."""
    if not time_str or not time_str.strip():
        return None
        
    # Clean the string - remove wind readings and other non-time data
    cleaned = re.sub(r'\s*[\+\-]?\d*\.?\d*\s*$', '', time_str.strip())  # Remove wind
    cleaned = re.sub(r'[^0-9.:]', '', cleaned)
    
    if not cleaned:
        return None
        
    try:
        if ':' in cleaned:
            # Format like "1:48.23" 
            parts = cleaned.split(':')
            if len(parts) == 2:
                mins = int(parts[0])
                secs = float(parts[1])
                total = mins * 60 + secs
                return Decimal(str(total)).quantize(Decimal('0.01'))
        else:
            # Format like "48.23" (seconds only)
            total = float(cleaned)
            return Decimal(str(total)).quantize(Decimal('0.01'))
    except (ValueError, Exception) as e:
        logger.debug(f"Could not parse time '{time_str}': {e}")
        return None
    
    return None


def _create_selenium_driver() -> webdriver.Chrome:
    """Create a Chrome driver with anti-detection options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")  # Try without JS first
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
    
    # Anti-detection measures
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def _try_requests_approach(url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
    """Try to get page content using requests with retry logic."""
    for attempt in range(max_retries):
        try:
            # Random delay between requests
            delay = random.uniform(2.0, 5.0)
            time.sleep(delay)
            
            headers = _get_random_headers()
            
            # Create session for better connection handling
            session = requests.Session()
            session.headers.update(headers)
            
            logger.info(f"Attempt {attempt + 1}: Requesting {url}")
            resp = session.get(url, timeout=20)
            
            if resp.status_code == 200:
                logger.info(f"Success! Got {len(resp.content)} bytes")
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Check if we got actual content (not blocked)
                if soup.find('title') and len(soup.get_text().strip()) > 500:
                    return soup
                else:
                    logger.warning(f"Page content appears to be blocked or empty")
                    
            elif resp.status_code == 403:
                logger.warning(f"403 Forbidden - anti-bot protection detected")
                # Longer delay before retry
                time.sleep(random.uniform(10.0, 20.0))
                
            else:
                logger.warning(f"HTTP {resp.status_code}: {resp.reason}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed: {e}")
            
    return None


def _try_selenium_approach(url: str) -> Optional[BeautifulSoup]:
    """Fallback to Selenium with improved anti-detection."""
    driver = None
    try:
        logger.info("Trying Selenium approach...")
        driver = _create_selenium_driver()
        driver.set_page_load_timeout(30)
        
        # Navigate to the page
        driver.get(url)
        
        # Wait a bit for any dynamic content
        time.sleep(random.uniform(3.0, 7.0))
        
        # Check if page loaded successfully
        title = driver.title
        if not title or 'error' in title.lower() or 'forbidden' in title.lower():
            logger.warning(f"Selenium detected blocked page: '{title}'")
            return None
            
        # Get page source
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        logger.info(f"Selenium retrieved {len(html)} characters")
        return soup
        
    except (TimeoutException, WebDriverException) as e:
        logger.error(f"Selenium error: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def parse_athlete_data(soup: BeautifulSoup) -> List[Dict]:
    """Parse athlete data from the TFRRS page using the actual HTML structure."""
    athletes = []
    
    # Based on the webpage content we analyzed, look for the actual data structure
    # The data appears to be in tables with athlete information
    
    # Try multiple table selectors
    tables = soup.find_all('table')
    logger.info(f"Found {len(tables)} tables on page")
    
    for table_idx, table in enumerate(tables):
        logger.debug(f"Processing table {table_idx + 1}")
        
        # Look for rows that contain athlete data
        rows = table.find_all('tr')
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 4:  # Need at least rank, name, school, time
                continue
                
            # Extract text from cells
            cell_texts = [cell.get_text().strip() for cell in cells]
            
            # Skip header rows
            if any(header_word in cell_texts[0].lower() for header_word in ['rank', 'place', '#']):
                continue
                
            # Try to identify athlete data pattern
            # Expected: [rank, name, school/team, time, ...]
            try:
                rank_text = cell_texts[0]
                name_text = cell_texts[1] if len(cell_texts) > 1 else ""
                school_text = cell_texts[2] if len(cell_texts) > 2 else ""
                time_text = cell_texts[3] if len(cell_texts) > 3 else ""
                
                # Validate rank (should be numeric)
                try:
                    rank = int(re.sub(r'[^\d]', '', rank_text))
                except ValueError:
                    continue
                    
                # Validate name (should contain letters)
                if not re.search(r'[a-zA-Z]', name_text):
                    continue
                    
                # Parse time
                performance_time = _parse_time_to_seconds(time_text)
                if performance_time is None:
                    continue
                    
                # Split name into first/last
                name_parts = name_text.split()
                if len(name_parts) < 2:
                    continue
                    
                first_name = name_parts[0].lower()
                last_name = ' '.join(name_parts[1:]).lower()
                
                # Determine event - for now, use a placeholder
                # This would need to be determined from page context
                event = "unknown_event"
                
                athlete_data = {
                    'rank': rank,
                    'first_name': first_name,
                    'last_name': last_name,
                    'college_team': school_text,
                    'event': event,
                    'performance_time': performance_time,
                    'year_scraped': datetime.now().year,
                    'raw_performance': time_text,
                    'scrape_timestamp': datetime.now()
                }
                
                athletes.append(athlete_data)
                logger.debug(f"Parsed athlete: {first_name} {last_name} - {school_text} - {time_text}")
                
            except Exception as e:
                logger.debug(f"Error parsing row {row_idx}: {e}")
                continue
    
    logger.info(f"Successfully parsed {len(athletes)} athletes")
    return athletes


def scrape_event_page(url: str, config: Dict) -> List[Dict]:
    """Scrape a single TFRRS page and return athlete data."""
    logger.info(f"Scraping {url}")
    
    # Try requests approach first
    soup = _try_requests_approach(url)
    
    # Fall back to Selenium if needed
    if soup is None:
        logger.info("Requests failed, trying Selenium...")
        soup = _try_selenium_approach(url)
    
    if soup is None:
        logger.error(f"Failed to retrieve content from {url}")
        return []
    
    # Parse the athlete data
    athletes = parse_athlete_data(soup)
    
    # Limit to configured maximum
    max_athletes = config['scraping']['max_athletes_per_page']
    if len(athletes) > max_athletes:
        athletes = athletes[:max_athletes]
        logger.info(f"Limited results to {max_athletes} athletes")
    
    return athletes


def store_athletes(athletes: List[Dict]) -> None:
    """Upsert scraped athlete records into the database."""
    if not athletes:
        logger.info("No athletes to store")
        return
        
    engine = get_engine()
    try:
        with Session(engine) as session:
            for data in athletes:
                runner = Runner(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    college_team=data['college_team'],
                    event=data['event'],
                    performance_time=data['performance_time'],
                    year=data['year_scraped'],
                    gender='M',  # TODO: Determine from page context
                    birth_year=None,
                    scrape_timestamp=data['scrape_timestamp'],
                    raw_data={'raw_performance': data['raw_performance'], 'scrape_source': 'TFRRS'}
                )
                session.merge(runner)
            session.commit()
            logger.info(f"Successfully stored {len(athletes)} athletes")
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


def main(config_path: str = 'config/events.yaml'):
    """Main scraping function."""
    try:
        cfg = yaml.safe_load(Path(config_path).read_text())
        Path('logs').mkdir(exist_ok=True)
        
        total_athletes = 0
        successful_urls = 0
        failed_urls = 0
        
        for url in cfg['list_urls']:
            try:
                athletes = scrape_event_page(url, cfg)
                if athletes:
                    store_athletes(athletes)
                    total_athletes += len(athletes)
                    successful_urls += 1
                else:
                    failed_urls += 1
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                failed_urls += 1
                
        logger.info(f"=== Scraping Summary ===")
        logger.info(f"Total athletes scraped: {total_athletes}")
        logger.info(f"Successful URLs: {successful_urls}")
        logger.info(f"Failed URLs: {failed_urls}")
        logger.info(f"Success rate: {successful_urls/(successful_urls+failed_urls)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TFRRS Scraper with anti-bot protection')
    parser.add_argument('--config', default='config/events.yaml', help='Configuration file path')
    args = parser.parse_args()
    main(args.config)
