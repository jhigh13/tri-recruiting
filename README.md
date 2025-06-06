# USA Triathlon Talent ID Pipeline

Automate the identification of NCAA Division I track athletes with competitive swimming backgrounds to discover potential triathlon talent.

## Overview

This pipeline:
1. Scrapes top NCAA Division I track athletes from TFRRS (past 5 years)
2. Cross-references with SwimCloud to find swimming histories  
3. Matches athletes using fuzzy logic algorithms
4. Classifies performance against USA Triathlon time standards
5. Generates Excel reports with color-coded classifications

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
│   ├── scrape_tfrrs.py    # TFRRS scraper  
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
