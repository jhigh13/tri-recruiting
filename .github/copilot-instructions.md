# GitHub Copilot Custom Instructions

## Project Context
- Automate a pipeline to identify NCAA Division I runners, match them to SwimCloud profiles, and classify performance against USA Triathlon time standards.
- Use Python 3.11+ for all scripts. 
- All CLI commands and scripts must run in PowerShell (no WSL/bash).

## Code Style & Conventions
- Follow PEP 8 for formatting and naming. Use type hints for all function signatures.
- Prefer descriptive variable names (e.g., `runner_id`, `match_score`).
- Keep functions under ~50 lines; extract helpers for longer logic.
- Use f-strings for string interpolation.
- Use constants (e.g., `MATCH_THRESHOLD = 90`) instead of magic numbers.

## Repository Structure
- Keep top-level folders minimal; Copilot should infer from file naming:
├── etl/
│ ├── scrape_tfrrs.py
│ ├── scrape_swimcloud.py
│ ├── data_cleaning.py
│ ├── matcher.py
│ ├── classifier.py
│ └── standards_loader.py
├── db/
│ ├── models.py
│ ├── create_tables.py
│ └── db_connection.py
├── config/
│ └── events.yaml
├── reports/
│ └── report_generator.py
├── automation/
│ └── run_pipeline.ps1
├── data/
│ └── time_standards.csv
├── tests/
│ ├── test_time_conversion.py
│ ├── test_match_score.py
│ └── test_classifier.py
├── .pre-commit-config.yaml
├── requirements.txt
├── README.md
├── setup.ps1
└── .env.example

## Environment & Dependencies
- Use a Python virtual environment (`.venv`) via `setup.ps1`.
- Pin dependencies in `requirements.txt`; do not install unpinned versions.
- Use Docker Compose only for PostgreSQL (see `docker/postgres-compose.yml`).
- Store secrets (`DATABASE_URL`, `OPENAI_API_KEY`, `CHROMEDRIVER_PATH`) in `.env` (refer to `.env.example`).

## Matching & Scoring
- Implement scoring exactly as
:total_score = (name_ratio * 0.6)
+ hometown_bonus
+ birth_year_bonus
+ school_bonus

If total_score ≥ 90 → auto_verify
If 70 ≤ total_score < 90 → manual_review
Else → no_match

- Use `rapidfuzz.token_set_ratio` for name comparisons.
- Include a text explanation of which fields contributed to the score.

*(Detailed scoring logic and thresholds should live as docstrings/comments in `matcher.py`.)*

## Scraping Guidelines
- Use `requests` + `BeautifulSoup` for static pages; fall back to headless Selenium only when JavaScript is required.
- Implement polite scraping: set a custom User-Agent and add `time.sleep(1–2)` between requests.
- Keep HTML examples (from `examples.md`) next to parsing code to guide selector usage.

## Database & ORM
- Use SQLAlchemy declarative models in `db/models.py`.
- Wrap session commits in try/except and always close sessions in `finally`.
- Use `session.merge()` for upserting `Runner` and `Swimmer` records.

*(Keep any ER diagrams or detailed relationship notes inside `models.py` as comments.)*

## Testing Practices
- Use `pytest` for unit and integration tests under `tests/`.
- Mock external HTTP calls (e.g., in `scrape_tfrrs.py`, `scrape_swimcloud.py`) to avoid real requests.
- Ensure test output is text-only (use `pytest --color=no` in CI).

## Reporting & Accessibility
- When generating Excel, include a “Tier” column alongside cell colors.
- In CSV exports, add a `color_label` text field (`Dark_Green`, `Green`, `Yellow`, `Red`) so screen readers can convey classification.

*(Detailed formatting notes belong in `report_generator.py`.)*

## Pull Request & Commit Conventions
- Write commit messages in imperative tense (e.g., “Add TFRRS scraping logic”).
- Each PR should reference an issue number and include a brief description.

*(Consider a separate `CONTRIBUTING.md` for more elaborate contribution guidelines.)*
