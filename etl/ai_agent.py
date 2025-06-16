"""
AI Agent module for SwimCloud matching.
"""
import asyncio
import logging
import os
from typing import List, Dict
import shelve
import requests
from bs4 import BeautifulSoup
import time
import random
import json
from rapidfuzz.fuzz import token_set_ratio
import csv
from pathlib import Path

# Add project root to path for module imports
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Database connection for runner retrieval and match updates
from db.db_connection import get_session
from db.models import Runner, Swimmer, RunnerSwimmerMatch
from sqlalchemy.exc import SQLAlchemyError

# HTTP client and environment variable loading
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient

# Load environment variables
load_dotenv()

AZURE_AGENT_ENDPOINT = os.getenv('AZURE_PROJECT_ENDPOINT')
AZURE_AGENT_ID = os.getenv('AZURE_AGENT_ID')
if not AZURE_AGENT_ENDPOINT or not AZURE_AGENT_ID:
    logging.error("AZURE_AGENT_ENDPOINT and AZURE_AGENT_ID must be set in environment.")
    raise RuntimeError("Azure AI Foundry Agent configuration missing.")
CACHE_FILE = 'search_cache.db'


# Load existing cache from disk
def _load_cache() -> dict[str, list[dict]]:
    try:
        with shelve.open(CACHE_FILE) as shelf:
            return dict(shelf)
    except Exception:
        return {}


SEARCH_CACHE: dict[str, list[dict]] = _load_cache()


def get_runners() -> List[Dict]:
    """Retrieve all runners from the database for SwimCloud matching."""
    session = get_session()
    try:
        runners = session.query(Runner).all()
        runner_list: List[Dict] = []
        for r in runners:
            runner_list.append({
                "runner_id": r.runner_id,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "college_team": r.college_team,
                "hometown": r.hometown,
                "birth_year": r.birth_year,
            })
        return runner_list
    finally:
        session.close()


def build_search_query(runner: Dict) -> str:
    """Build a Bing search query string using runner attributes."""
    parts = [runner['first_name'], runner['last_name'], 'swim profile']
    if runner.get('college_team'):
        parts.append(runner['college_team'])
    if runner.get('hometown'):
        parts.append(runner['hometown'])
    return ' '.join(parts)


async def bing_search_async(query: str) -> list[dict]:
    """Perform an asynchronous search via Azure AI Foundry Agent and return results with caching."""
    if query in SEARCH_CACHE:
        return SEARCH_CACHE[query]
    # Use Azure AI Foundry Agent SDK in executor
    def sync_agent_search() -> list[dict]:
        credential = DefaultAzureCredential()
        client = AgentsClient(
            endpoint=AZURE_AGENT_ENDPOINT,
            credential=credential
        )
        # The request to the agent should include our query
        response = client.invoke(agent_id=AZURE_AGENT_ID, request=query)
        items = response.get('results', []) if isinstance(response, dict) else []
        return [{'name': item.get('name'), 'url': item.get('url')} for item in items]

    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, sync_agent_search)
    # Cache and persist
    SEARCH_CACHE[query] = results
    try:
        with shelve.open(CACHE_FILE) as shelf:
            shelf[query] = results
    except Exception as e:
        logging.warning(f"Failed to write cache to disk: {e}")
    return results


SCRAPE_DELAY = float(os.getenv('SCRAPE_DELAY', '2'))
USER_AGENT = os.getenv('USER_AGENT', 'USA-Triathlon-TalentID-Pipeline/1.0')


def get_and_parse_candidate(url: str) -> Dict:
    """
    Fetch and parse a SwimCloud profile page, extracting name, hometown,
    birth year (if available), swim team, and best times.
    """
    headers = {'User-Agent': USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    # Polite delay
    time.sleep(SCRAPE_DELAY + random.uniform(0, 1))
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Parse JSON-LD for basic profile info
    profile = {}
    script = soup.find('script', type='application/ld+json')
    if script:
        try:
            data = json.loads(script.string)
            profile['name'] = data.get('name', '').strip()
            loc = data.get('homeLocation', {})
            city = loc.get('addressLocality', '')
            region = loc.get('addressRegion', '')
            profile['hometown'] = f"{city}, {region}".strip(', ')
        except json.JSONDecodeError:
            profile['name'] = ''
            profile['hometown'] = ''
    else:
        profile['name'] = ''
        profile['hometown'] = ''

    # Birth year: not directly in JSON-LD; placeholder None
    profile['birth_year'] = None

    # Swim team: example selector, may need adjustment
    team_tag = soup.select_one('.c-sc-profile__header .team-name')
    profile['swim_team'] = team_tag.text.strip() if team_tag else None

    # Best times: parse table rows (placeholder)
    profile['best_times'] = {}
    time_rows = soup.select('table.times-table tbody tr')
    for row in time_rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            event_name = cols[0].text.strip().replace(' ', '_')
            time_text = cols[1].text.strip()
            # Convert time_text to seconds (helper to implement)
            profile['best_times'][event_name] = time_text

    profile['swimcloud_url'] = url
    return profile


# Scoring constants
MATCH_THRESHOLD = 90
MANUAL_THRESHOLD = 70
HOMETOWN_EXACT_BONUS = 20
HOMETOWN_FUZZY_BONUS = 10
BIRTH_YEAR_EXACT_BONUS = 15
BIRTH_YEAR_OFF_BY_ONE_BONUS = 5
SCHOOL_FUZZY_BONUS = 10


def compute_match_score(runner: Dict, candidate: Dict) -> tuple[int, str]:
    """
    Compute a match score between a runner and a SwimCloud candidate.
    Returns (total_score, explanation).
    """
    explanation_parts: list[str] = []
    runner_name = f"{runner['first_name']} {runner['last_name']}"
    candidate_name = candidate.get('name', '')
    name_ratio = token_set_ratio(runner_name, candidate_name)
    explanation_parts.append(f"name_ratio={name_ratio}")

    # Reject if name_ratio < 75
    if name_ratio < 75:
        explanation = f"Name ratio {name_ratio} below 75: no match."
        return 0, explanation

    # Hometown bonus
    hometown_bonus = 0
    r_ht = runner.get('hometown') or ''
    c_ht = candidate.get('hometown') or ''
    if r_ht and c_ht:
        if r_ht.lower() == c_ht.lower():
            hometown_bonus = HOMETOWN_EXACT_BONUS
            explanation_parts.append(f"hometown_exact_bonus={HOMETOWN_EXACT_BONUS}")
        else:
            ht_ratio = token_set_ratio(r_ht, c_ht)
            if ht_ratio >= 80:
                hometown_bonus = HOMETOWN_FUZZY_BONUS
                explanation_parts.append(f"hometown_fuzzy_bonus={HOMETOWN_FUZZY_BONUS}")
    
    # Birth year bonus
    birth_bonus = 0
    r_by = runner.get('birth_year')
    c_by = candidate.get('birth_year')
    if r_by and c_by:
        if r_by == c_by:
            birth_bonus = BIRTH_YEAR_EXACT_BONUS
            explanation_parts.append(f"birth_year_exact_bonus={BIRTH_YEAR_EXACT_BONUS}")
        elif abs(r_by - c_by) == 1:
            birth_bonus = BIRTH_YEAR_OFF_BY_ONE_BONUS
            explanation_parts.append(f"birth_year_off_by_one_bonus={BIRTH_YEAR_OFF_BY_ONE_BONUS}")

    # School/team bonus
    school_bonus = 0
    r_team = runner.get('college_team') or ''
    c_team = candidate.get('swim_team') or ''
    if r_team and c_team:
        team_ratio = token_set_ratio(r_team, c_team)
        if team_ratio >= 80:
            school_bonus = SCHOOL_FUZZY_BONUS
            explanation_parts.append(f"school_fuzzy_bonus={SCHOOL_FUZZY_BONUS}")

    # Total score
    total_score = int((name_ratio * 0.9) + hometown_bonus + birth_bonus + school_bonus)
    explanation_parts.append(f"total_score={total_score}")
    explanation = "; ".join(explanation_parts)
    return total_score, explanation


def upsert_swimmer(candidate: Dict) -> int:
    """Insert or update a Swimmer record and return its ID."""
    session = get_session()
    try:
        # Extract swimmer_id from URL: '/swimmer/{id}/'
        url = candidate.get('swimcloud_url', '')
        swimmer_id = None
        if url:
            parts = url.rstrip('/').split('/')
            if parts and parts[-2] == 'swimmer':
                swimmer_id = int(parts[-1])
        swimmer = Swimmer(
            swimmer_id=swimmer_id,
            first_name=candidate.get('name', '').split(' ')[0].lower(),
            last_name=candidate.get('name', '').split(' ')[-1].lower(),
            hometown=candidate.get('hometown'),
            birth_year=candidate.get('birth_year'),
            swim_team=candidate.get('swim_team'),
            best_times=candidate.get('best_times'),
            swimcloud_url=candidate.get('swimcloud_url'),
            raw_swim_json=candidate  # store entire dict
        )
        merged = session.merge(swimmer)
        session.commit()
        return merged.swimmer_id
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"Failed to upsert swimmer: {e}")
        raise
    finally:
        session.close()


def update_match_record(runner_id: int, swimmer_id: int, score: int, status: str, explanation: str) -> None:
    """Insert or update a RunnerSwimmerMatch record."""
    session = get_session()
    try:
        # Determine matched fields array
        fields = []
        if 'name_ratio' in explanation:
            fields.append('name')
        if 'hometown' in explanation:
            fields.append('hometown')
        if 'birth_year' in explanation:
            fields.append('birth_year')
        if 'school' in explanation:
            fields.append('school')

        match = RunnerSwimmerMatch(
            runner_id=runner_id,
            swimmer_id=swimmer_id,
            match_score=score,
            match_explanation=explanation,
            verification_status=status,
            matched_on_fields=fields
        )
        session.merge(match)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"Failed to upsert match record: {e}")
    finally:
        session.close()


def export_manual_review(output_path: str = 'manual_review.csv') -> None:
    """
    Export all manual_review match records to a CSV for human review.
    Columns: runner_id, first_name, last_name, swimcloud_url, match_score, verification_status, match_explanation
    """
    session = get_session()
    try:
        matches = session.query(RunnerSwimmerMatch).filter(
            RunnerSwimmerMatch.verification_status == 'manual_review'
        ).all()
        if not matches:
            logging.info('No manual_review matches to export.')
            return

        fieldnames = [
            'runner_id', 'first_name', 'last_name',
            'swimcloud_url', 'match_score', 'verification_status', 'match_explanation'
        ]
        output_file = Path(output_path)
        with output_file.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for m in matches:
                runner = m.runner
                swimmer = m.swimmer
                writer.writerow({
                    'runner_id': runner.runner_id,
                    'first_name': runner.first_name,
                    'last_name': runner.last_name,
                    'swimcloud_url': swimmer.swimcloud_url,
                    'match_score': float(m.match_score),
                    'verification_status': m.verification_status,
                    'match_explanation': m.match_explanation
                })
        logging.info(f'Exported {len(matches)} manual_review records to {output_path}')
    finally:
        session.close()


# Update process_all_runners to tie everything together
async def process_all_runners() -> None:
    """Process all runners asynchronously to find SwimCloud matches."""
    logging.info("Starting AI agent runner processing...")
    runners = get_runners()[:10]  # limit for testing
    for runner in runners:
        query = build_search_query(runner)
        logging.info(f"Searching Bing for: {query}")
        results = await bing_search_async(query)
        urls = [r['url'] for r in results if 'swimcloud.com/swimmer' in r['url']]
        for url in urls:
            try:
                candidate = get_and_parse_candidate(url)
                score, explanation = compute_match_score(runner, candidate)
                if score >= MATCH_THRESHOLD:
                    status = 'auto_verified'
                elif score >= MANUAL_THRESHOLD:
                    status = 'manual_review'
                else:
                    status = 'no_match'
                swimmer_id = upsert_swimmer(candidate)
                update_match_record(runner['runner_id'], swimmer_id, score, status, explanation)
                logging.info(f"Recorded match: runner {runner['runner_id']} ↔ swimmer {swimmer_id} status={status} score={score}")
            except Exception as e:
                logging.error(f"Error processing candidate {url}: {e}")
    logging.info("Processing complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(process_all_runners())
