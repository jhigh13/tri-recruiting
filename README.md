# USA Triathlon Talent ID Pipeline

Automate the identification of NCAA Division I track athletes with competitive swimming backgrounds to discover potential triathlon talent.

## Overview

This pipeline:
1. Extract distance running performances from TFRRS HTML (etl/scrape_tfrrs.py, tfrrs_html_processor_new.py).  
2. Clean & normalize runner data (etl/data_cleaning.py).  
3. Load USA Triathlon standards and classify performances (etl/standards_loader.py, etl/classifier.py).  
4. **AI Agent SwimCloud Matching**  
   - For each runner, invoke an AI agent that:  
     • Searches SwimCloud for possible profiles  
     • Extracts profile info via headless Selenium or HTML parsing  
     • Computes a match score and auto‐verifies or flags for review  
   - Stores match metadata back into the database.  
5. Generate reports (reports/report_generator.py) and export to CSV/Excel with accessibility labels.  
6. Automate entire flow via PowerShell wrapper (automation/run_pipeline.ps1).

## Quick Start

### Prerequisites
- Python 3.11 or higher
- PowerShell (Windows)

### Setup Instructions

1. **Clone and setup environment:**
   ```powershell
   git clone <repository-url>
   cd tri-recruiting
   .\setup.ps1
   ```

2. **Create database tables:**
   ```powershell
   python db/create_tables.py
   ```

3. **Load time standards:**
   ```powershell
   python etl/extract_standards.py
   python etl/standards_loader.py
   ```

4. **Run the pipeline:**
   ```powershell
   .\automation\run_pipeline.ps1
   ```

## Project Structure

```
├── etl/                    # Data extraction and processing
│   ├── tfrrs_html_processor.py    # TFRRS html processor  
│   ├── scrape_swimcloud.py # SwimCloud scraper
│   ├── matcher.py         # Fuzzy matching logic
│   └── classifier.py      # Performance classification
├── db/                    # Database models and setup
├── config/                # Configuration files
├── reports/               # Report generation
├── automation/            # Pipeline orchestration
├── data/                  # Static data files
└── tests/                 # Unit and integration tests
```

## Configuration

Key settings in `.env`:
- `DATABASE_URL`: SQLite database file path (default: sqlite:///data/tri_talent.db)
- `CHROMEDRIVER_PATH`: Path to ChromeDriver executable  
- `SCRAPE_DELAY`: Seconds between requests (default: 2)
- `YEARS_TO_SCRAPE`: Historical data range (default: 5)

## Matching Algorithm

Athletes are matched using a weighted scoring system:
- **Name similarity (60%)**: Using rapidfuzz token_set_ratio
- **Hometown bonus**: +15 points for matching location
- **Birth year bonus**: +10 points for exact match, +5 for ±1 year
- **School bonus**: +15 points for matching institution

**Thresholds:**
- ≥90: Auto-verified match
- 70-89: Manual review required  
- <70: No match

## Output Classifications

Based on USA Triathlon time standards:
- **Dark Green**: World Leading potential
- **Green**: Internationally Ranked  
- **Yellow**: Nationally Competitive
- **Red**: Development Potential

## Development

Run tests:
```powershell
pytest --color=no
```

Format code:
```powershell
black .
isort .
```

## License

[License information]
automate USA Triathlon recruitment process.

## Data Model

### Runner (db/models.py)
| Column                   | Type       | Description                                        |
|--------------------------|------------|----------------------------------------------------|
| id                       | Integer PK | Unique runner ID                                   |
| first_name               | String     | Lowercased first name                              |
| last_name                | String     | Lowercased last name                               |
| college_team             | String     | School name                                        |
| event                    | String     | Normalized event (e.g. “5000m”)                    |
| performance_time         | Decimal    | Seconds (with two decimals)                        |
| year                     | Integer    | Year scraped                                       |
| gender                   | Char(1)    | “M” or “F”                                         |
| **swimcloud_profile_url**       | String     | URL of matched SwimCloud profile (nullable)        |
| **swimcloud_match_score**       | Integer    | 0–100 score from rapidfuzz + bonuses               |
| **swim_background_flag**        | Boolean    | True if auto_verified ≥ MATCH_THRESHOLD            |
| **swimcloud_raw_data**          | JSON       | Raw extracted SwimCloud fields (e.g. best times)   |
| scrape_timestamp         | DateTime   | When TFRRS data was scraped                        |
| swimcloud_search_timestamp | DateTime | When SwimCloud lookup was performed                |
