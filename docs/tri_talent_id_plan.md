````markdown
# Implementation Plan f-  - [x] **Step 1: - [x] **Step 2: Database Schema & Connection Layer**epository & Environment Setup** **Files** (4)
    - `README.md`: Update with add environment setup instructions.
    - `requirements.txt`: pin `python >=3.11`, `pandas`, `sqlalchemy`, `requests`, `beautifulsoup4`, `rapidfuzz`, `openpyxl`, `selenium`, `python-dotenv`, `pdfplumber`.
    - `.pre-commit-config.yaml`: enable black, isort, flake8.
    - `setup.ps1`: **pseudocode** –**Step 3: E- [ ] **Step 4: TFRRS Scraper Module**
  - **Task**: Fetch top 500 Division I athletes per event/season for past 5 years, normalise times, upsert into `runners`.
  - **Files** (3)
    - `etl/scrape_tfrrs.py`: **pseudocode** –
      ```python
      for year in range(2020, 2026):  # Past 5 years
          for event_url in DIVISION_I_EVENT_URLS:
              html = requests.get(event_url).text
              soup = BeautifulSoup(html)
              for row in parse_rows(soup):
                  runner = Runner(...)
                  session.merge(runner)
      ```
    - `config/events.yaml`: mapping of Division I event ids → names.
    - `etl/request_cache.py`: simple file-based caching to avoid re-scraping.
  - **Dependencies**: requests, BeautifulSoup, SQLAlchemy.
  - **User Action** ➜ none (automated).
  - **Accessibility Note**: log progress with clear text; no reliance on colour logs.Time Standards Data**
  - **Task**: Extract time standards from PDF, create `time_standards.csv`, write loader script.
  - **Files** (3)
    - `etl/extract_standards.py`: extract data from "Time Standards Explanation.pdf" and create CSV.
    - `etl/standards_loader.py`: read CSV → insert rows.
    - `data/time_standards.csv`: extracted cutoff list (auto-generated from PDF).
  - **Dependencies**: pandas, PyPDF2 or pdfplumber.
  - **User Action** ➜ verify extracted values match PDF before first import.
  - **Accessibility Note**: include plain‑text column for colour label, not just colour hex, for screen readers.hlon_talent_id_detailed_spec.md

---

## Legend
-   **User Action** ➜ steps that require human intervention.
-   **Accessibility Note** ➜ consideration to keep pipeline outputs usable by assistive technology (e.g., screen‑readers, colour‑blind friendly visualisations).

---

- [ ] **Step 1: Repository & Environment Setup**
  - **Task**: Create Python virtual environment, install baseline dependencies, configure pre‑commit hooks.
  - **Files** (4)
    - `README.md`: Update with add environment setup instructions.
    - `requirements.txt`: pin `python >=3.11`, `pandas`, `sqlalchemy`, `requests`, `beautifulsoup4`, `rapidfuzz`, `openpyxl`, `selenium`, `python-dotenv`.
    - `.pre-commit-config.yaml`: enable black, isort, flake8.
    - `setup.ps1`: **pseudocode** –
      ```powershell
      python -m venv .venv
      .\.venv\Scripts\Activate.ps1
      pip install -r requirements.txt
      ```
  - **Dependencies**: Git, Python 3.11, PowerShell.
  - **User Action** ➜ run `setup.ps1` and commit initial structure.
  - **Accessibility Note**: document CLI usage in README with alternative commands for macOS/Linux.

- [ ] **Step 2: Database Schema & Connection Layer**
  - **Task**: Define ORM models, create migration script, spin up local PostgreSQL container.
  - **Files** (3)
    - `db/models.py`: ORM classes for `Runner`, `Swimmer`, `TimeStandard`, `RunnerSwimmerMatch`, `Classification` (**pseudocode only**).
    - `db/create_tables.py`: script that calls `Base.metadata.create_all(engine)`.
    - `docker/postgres-compose.yml`: minimal Docker Compose file: Postgres 15, volume mount.
  - **Dependencies**: Docker Desktop, SQLAlchemy.
  - **User Action** ➜ run `docker compose up -d` then `python db/create_tables.py`.
  - **Accessibility Note**: expose env vars for DB creds via `.env` to avoid hard‑coding.

- [ ] **Step 3: Load Time Standards Seed Data**
  - **Task**: Convert attached PDF/CSV to `time_standards.csv`; write loader script.
  - **Files** (2)
    - `etl/standards_loader.py`: read CSV → insert rows.
    - `data/time_standards.csv`: curated cutoff list (manual entry).
  - **Dependencies**: pandas.
  - **User Action** ➜ verify values in CSV match USA Triathlon sheet before first import.
  - **Accessibility Note**: include plain‑text column for colour label, not just colour hex, for screen readers.

- [ ] **Step 4: TFRRS Scraper Module**
  - **Task**: Fetch top 500 per event/season, normalise times, upsert into `runners`.
  - **Files** (2)
    - `etl/scrape_tfrrs.py`: **pseudocode** –
      ```python
      for event_url in EVENT_URLS:
          html = requests.get(event_url).text
          soup = BeautifulSoup(html)
          for row in parse_rows(soup):
              runner = Runner(...)
              session.merge(runner)
      ```
    - `config/events.yaml`: mapping of event ids → names.
  - **Dependencies**: requests, BeautifulSoup, SQLAlchemy.
  - **User Action** ➜ none (automated).
  - **Accessibility Note**: log progress with clear text; no reliance on colour logs.

- [ ] **Step 5: SwimCloud Scraper Module**
  - **Task**: For each un‑matched runner, search SwimCloud, scrape candidate profiles, store into `swimmers` table.
  - **Files** (2)
    - `etl/scrape_swimcloud.py`: supports headless Selenium when JavaScript search required.
    - `etl/utils/swim_parsers.py`: helper to extract hometown, birth year, best times.
  - **Dependencies**: requests, BeautifulSoup, Selenium, rapidfuzz.
  - **User Action** ➜ supply ChromeDriver path via environment variable.
  - **Accessibility Note**: build retry/back‑off to avoid captchas—avoids forcing manual CAPTCHA challenges.

- [ ] **Step 6: Data Cleaning & Normalisation**
  - **Task**: Standardise names, convert times to seconds, tokenise hometown & team.
  - **Files** (1)
    - `etl/data_cleaning.py`: functions `clean_name`, `time_to_seconds`, etc.
  - **Dependencies**: pandas.
  - **Accessibility Note**: ensure functions raise descriptive exceptions for easier debugging with screen readers.

- [ ] **Step 7: Matching Algorithm Implementation**
  - **Task**: Calculate `match_score`, insert into `RunnerSwimmerMatch`.
  - **Files** (1)
    - `matcher.py`: **pseudocode** –
      ```python
      for runner in session.query(Runner).filter(~Runner.matches.any()):
          candidates = find_candidates(runner)
          for swim in candidates:
              score = compute_score(runner, swim)
              match = RunnerSwimmerMatch(...)
              session.add(match)
      ```
  - **Dependencies**: rapidfuzz.
  - **User Action** ➜ none initially.
  - **Accessibility Note**: write textual justification string per match (fields matched) for audit logs.

- [ ] **Step 8: Manual Review Export & Import**
  - **Task**: Output "manual_review.csv" for matches 70–89; read reviewer decisions back in.
  - **Files** (2)
    - `etl/manual_review.py`: produce CSV with columns inc. `decision` placeholder.
    - `etl/apply_review.py`: read completed CSV, update `verification_status`.
  - **Dependencies**: pandas.
  - **User Action** ➜ manually inspect CSV, mark Y/N, save.
  - **Accessibility Note**: generate CSV with clear headers; avoid colour‑only cues.

- [ ] **Step 9: Classification Module**
  - **Task**: Compare swimmer times vs standards, insert `Classification` rows; assign colour label text + hex.
  - **Files** (1)
    - `classifier.py`: functions `classify_runner(runner)`; returns tier and colour.
  - **Dependencies**: pandas, SQLAlchemy.
  - **Accessibility Note**: include text description of tier in outputs.

- [ ] **Step 10: Report Generation**
  - **Task**: Export per‑event CSV & colour‑coded Excel; embed alt‑text for colour cells.
  - **Files** (2)
    - `reports/report_generator.py`: uses `openpyxl` to style rows.
    - `output/reports/` (dir): generated artefacts.
  - **Dependencies**: openpyxl.
  - **User Action** ➜ verify Excel conditional formatting displays correctly.
  - **Accessibility Note**: for colour‑blind users, include an additional column "Tier".

- [ ] **Step 11: Pipeline Orchestration Script**
  - **Task**: PowerShell wrapper to run steps 4 → 10 sequentially with logging.
  - **Files** (1)
    - `automation/run_pipeline.ps1`: **pseudocode** –
      ```powershell
      $steps = (
        'python etl/scrape_tfrrs.py',
        'python etl/scrape_swimcloud.py',
        'python matcher.py',
        'python etl/manual_review.py',
        # Wait for manual review...
        'python etl/apply_review.py',
        'python classifier.py',
        'python reports/report_generator.py'
      )
      foreach ($cmd in $steps) { & $cmd }
      ```
  - **Dependencies**: PowerShell 5+.
  - **User Action** ➜ schedule `run_pipeline.ps1` via Task Scheduler after each season.
  - **Accessibility Note**: log to `logs/execution_logs.log` with verbosity option.

- [ ] **Step 12: Build & End‑to‑End Test the Pipeline**
  - **Task**: Run the full pipeline on a single small event (e.g., top 20 athletes) to ensure DB writes, match logic, and reporting function.
  - **Files** (0) – executed via prior scripts.
  - **Dependencies**: all modules.
  - **User Action** ➜ review generated outputs, confirm classification accuracy.
  - **Accessibility Note**: provide a CLI flag `--limit 20` to make small‑scale test faster.

- [ ] **Step 13: Automated Tests**
  - **Task**: Write unit & integration tests (pytest) to verify scraper/parsers, matching score calculation, and classification thresholds.
  - **Files** (3)
    - `tests/test_time_conversion.py`
    - `tests/test_match_score.py`
    - `tests/test_classifier.py`
  - **Dependencies**: pytest, pytest‑cov.
  - **User Action** ➜ run `pytest -vv --cov` and fix failures.
  - **Accessibility Note**: ensure test output does not rely on colour (use `pytest --color=no` in CI).

- [ ] **Step 14: Continuous Integration & Documentation**
  - **Task**: Configure GitHub Actions to run tests on push, build Docker image (optional).
  - **Files** (2)
    - `.github/workflows/ci.yml`: installs deps, runs pytest.
    - `docs/USAGE.md`: guide for non‑technical staff.
  - **Dependencies**: GitHub Actions.
  - **User Action** ➜ set repository secrets for DB credentials if CI uses an ephemeral Postgres.
  - **Accessibility Note**: write `USAGE.md` with step‑by‑step and screenshots; include alt‑text on images.

# Do not implement step 15, inclusion of AI Agenet until I explicitly say so. This is will only be necessary if the performance of our code needs aid. 

- [ ] **Step 15: AI Agent–Assisted Accuracy Refinement** 


  - **Task**: Automatically review matches with score 70–89 using an LLM and either (a) confirm the match, (b) reject, or (c) leave for human review if confidence is still low.  
  - **Files** (2)  
    - `ai/agent_review.py`: wraps OpenAI API → feeds runner/swimmer JSON payload, returns decision + explanation.  
    - `config/agent_prompt.txt`: system/user prompt template with few-shot examples.  
  - **Dependencies**: `openai`, `python-dotenv` (for `OPENAI_API_KEY`).  
  - **Pseudocode**  
    ```python
    for m in session.query(RunnerSwimmerMatch).filter_by(verification_status='manual_review'):
        prompt = build_prompt(m.runner, m.swimmer, m.match_score)
        resp = call_llm(prompt)
        if resp.decision in ['ACCEPT','REJECT']:
            m.verification_status = 'auto_verified'
            m.ai_reason = resp.explanation
        else:
            # keep for human review
            pass
    session.commit()
    ```  
  - **User Action** ➜ Provide an API key, set a budget limit, and tune the `CONFIDENCE_THRESHOLD` env var.  
  - **Accessibility Note**: Store `ai_reason` text so screen-reader users can understand why the agent made a decision.


---
````
