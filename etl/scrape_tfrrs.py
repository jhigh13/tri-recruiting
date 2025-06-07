"""
TFRRS Scraper Module for NCAA Division I Track & Field Results.

This module scrapes top 500 athletes per event from TFRRS (Track & Field Results 
Reporting System) for the past several seasons, normalizes performance times, and stores
data in the runners table for matching against swimmers.

Key Features:
- Configurable URL list via YAML
- Robust error handling and rate limiting  
- Time normalization to seconds with validation
- Duplicate detection and upsert logic
- Progress tracking and logging

Usage:
    python etl/scrape_tfrrs.py --config config/events.yaml
"""
import argparse
import logging
import re
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
import requests_cache
import yaml
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from db.db_connection import get_engine
from db.models import Runner

# Configure logging
tlogging = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tfrrs_scraper.log'),
        logging.StreamHandler()
    ]
)


def _normalize_url(url: str) -> str:
    # Ensure consistent domain
    return url.replace("tf.tfrrs.org", "www.tfrrs.org").replace("m.tfrrs.org", "www.tfrrs.org")


def _parse_time_to_seconds(time_str: str) -> Optional[Decimal]:
    if not time_str or not time_str.strip():
        return None
    s = re.sub(r'[^0-9.:]', '', time_str.strip())
    if ':' in s:
        mins, secs = s.split(':')
        try:
            total = int(mins) * 60 + float(secs)
            return Decimal(str(total)).quantize(Decimal('0.01'))
        except:
            return None
    try:
        return Decimal(str(float(s))).quantize(Decimal('0.01'))
    except:
        return None


def scrape_event_page(url: str, config: Dict) -> List[Dict]:
    """
    Scrape a single TFRRS page (all events) and return athlete dicts.
    """
    athletes = []
    # cache to avoid repeat
    requests_cache.install_cache('tfrrs_cache', expire_after=86400)

    try:
        time.sleep(config['scraping']['request_delay_seconds'])
        resp = requests.get(_normalize_url(url), timeout=config['scraping']['timeout_seconds'])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')
        # find all event headers and tables
        headers = soup.select('h3, h4')
        tables = soup.select(config['selectors']['results_table'])
        for header, table in zip(headers, tables):
            event_name = header.get_text(strip=True)
            rows = table.select(config['selectors']['result_rows'])[1:config['scraping']['max_athletes_per_page']+1]
            for tr in rows:
                cols = [td.get_text(strip=True) for td in tr.find_all('td')]
                if len(cols) < 5:
                    continue
                rank, name, class_year, school, mark = cols[:5]
                seconds = _parse_time_to_seconds(mark)
                if not seconds:
                    continue
                athletes.append({
                    'rank': int(rank),
                    'first_name': name.split()[0].lower(),
                    'last_name': ' '.join(name.split()[1:]).lower(),
                    'college_team': school,
                    'event': event_name,
                    'performance_time': seconds,
                    'year_scraped': datetime.now().year,
                    'raw_performance': mark,
                    'scrape_timestamp': datetime.now()
                })
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
    return athletes


def store_athletes(athletes: List[Dict]) -> None:
    if not athletes:
        return
    engine = get_engine()
    with Session(engine) as session:
        for data in athletes:
            runner = Runner(
                first_name=data['first_name'],
                last_name=data['last_name'],
                college_team=data['college_team'],
                event=data['event'],
                performance_time=data['performance_time'],
                year=data['year_scraped'],
                gender=None,
                birth_year=None,
                scrape_timestamp=data['scrape_timestamp'],
                raw_data={'raw_performance': data['raw_performance'], 'scrape_source': 'TFRRS'}
            )
            session.merge(runner)
        session.commit()
        logging.info(f"Stored {len(athletes)} athletes.")


def main(config_path: str):
    cfg = yaml.safe_load(Path(config_path).read_text())
    Path('logs').mkdir(exist_ok=True)
    total = 0
    for url in cfg['list_urls']:
        logging.info(f"Processing {url}")
        aths = scrape_event_page(url, cfg)
        store_athletes(aths)
        total += len(aths)
    logging.info(f"Completed scraping. Total athletes: {total}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='config/events.yaml')
    args = p.parse_args()
    main(args.config)
