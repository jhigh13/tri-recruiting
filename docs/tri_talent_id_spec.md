# Detailed Specification: USA Triathlon Talent ID Pipeline

## Overview

This document outlines the detailed technical specification for automating the USA Triathlon talent identification pipeline. It includes precise data scraping instructions, data storage methods, matching logic, AI implementation, and a clear structure for the coding and automation process.

---

## 1. Technical Stack

### Backend

* **Language**: Python (3.11+)
* **Web Scraping Libraries**:

  * `BeautifulSoup`
* **Data Handling**:

  * `pandas`
  * `SQLAlchemy`
* **Database**:

  * SQLite
* **Fuzzy Matching**:

  * `rapidfuzz`

### Automation

* **Task Scheduling**:

  * Windows Task Scheduler (PowerShell scripts for automation)
* **Containerization (Optional)**:

  * Docker

---

## 2. Database Schema Creation (Completed)

Use `SQLAlchemy` with declarative syntax for Python ORM interaction with SQLite.

Tables:

* `runners`
* `swimmers`
* `time_standards`
* `runner_swimmer_match`
* `classification`

---

## 3. Web Scraping

### 3.1. TFRRS HTML Processing (Completed)

* Base URL: `https://tf.tfrrs.org`
* Events and qualifying pages as defined previously
* Extract top 500 athletes per event/season (Outdoor and Indoor)
* Data Points:

  * First Name
  * Last Name
  * Performance Time (convert to seconds)
  * School
  * Year
  * Gender
  * Event

### 3.2. SwimCloud Scraping

* URL: Search via `https://www.swimcloud.com/search/?q={name}`
* Scrape matching swimmer profiles
* Extract:

  * Name
  * Hometown
  * Birth Year (if available)
  * Swim Team
  * Best swim times per event (in seconds)

### 3.3. Time Standards (Completed)

* Manually compile into CSV and load into database for easy lookup.

---

## 4. Data Cleaning and Normalization

* Normalize athlete names (lowercase, remove punctuation/suffixes)
* Standardize hometown/school naming
* Store raw data snapshots as backup in JSONB columns (optional but recommended)

---

## 5. Matching Logic (Fuzzy Matching)

* Use `rapidfuzz` to match names:

  * `token_set_ratio` threshold: 90 for likely matches, 75-89 for manual review
* Secondary validation (hometown, birth year, team) with bonus scoring as previously outlined.

---

## 6. AI Agent for Verification (Optional)

* Leverage ChatGPT or Microsoft Foundry for ambiguous cases.
* Prompt the agent with scraped metadata for ambiguous matches.
* Integrate via OpenAI API or Azure OpenAI endpoints.

---

## 7. Classification Logic

* Compare swimmer best times against standards.
* Assign categories: World Leading, Internationally Ranked, Nationally Competitive, Development Potential, No Swim Background.
* Output a color-coded result.

---

## 8. Task Automation with PowerShell

* PowerShell script to execute:

  1. Python scripts sequentially (scrape TFRRS → scrape SwimCloud → matching → classification)
  2. Export final CSV or Excel reports
  3. Handle log creation and error notifications

---

## 9. Output and Visualization

* Initial outputs in Excel/CSV with classification color codes.
* Future dashboard integration with Power BI for visualizations.

---

## 10. Project Structure

```
project-root/
├── etl/
│   ├── scrape_tfrrs.py
│   ├── scrape_swimcloud.py
│   ├── data_cleaning.py
│   ├── matcher.py
│   ├── classifier.py
│   └── standards_loader.py
├── db/
│   ├── models.py
│   ├── create_tables.py
│   └── db_connection.py
├── output/
│   └── reports/
├── automation/
│   └── run_pipeline.ps1
├── logs/
│   └── execution_logs.log
├── config/
│   └── settings.ini
└── docs/
    ├── triathlon_talent_id_summary.md
    └── triathlon_talent_id_detailed_spec.md
```

---

## 11. Development Workflow

* Version control with GitHub.
* Feature branches for each component (scraping, matching, automation).
* Regular code reviews and incremental integration.

---

## 12. Next Steps

* Implement the initial database schema with SQLAlchemy.
* Begin coding scraping modules.
* Set up fuzzy matching and validation logic.
* Integrate AI components if necessary for ambiguous verification.

---

## 13. Additional Considerations for Future Development

### 13.1. Rate Limiting & Performance
- **Challenge**: Scraping 500 athletes × multiple events × 5 years could generate 10,000+ requests
- **Mitigation**: Implement aggressive rate limiting (2-3 seconds between requests), request caching, robust retry mechanisms
- **Future**: Consider reaching out to TFRRS/SwimCloud for API access or permission

### 13.2. Data Quality & Edge Cases
- **Name Variations**: Athletes using nicknames vs full names across platforms
- **School Transfers**: Track athletes who transfer schools mid-career
- **Temporal Misalignment**: Swimming times from years ago vs current track performance
- **Geographic Variations**: Different hometown representations

### 13.3. Scale Optimization
- **Matching Complexity**: Fuzzy matching could become O(n²) with large datasets
- **Pre-filtering**: Consider geographic region, age ranges, or conference-based filtering
- **Database Indexing**: Optimize queries with proper indexing on name, hometown, birth_year

### 13.4. Legal & Compliance
- **Terms of Service**: Review TFRRS and SwimCloud ToS regarding automated scraping
- **Data Retention**: Establish policies for how long to retain scraped data
- **Privacy**: Consider athlete privacy implications with cross-platform data matching

### 13.5. Error Handling & Monitoring
- **Website Changes**: Robust error handling when HTML structure changes
- **Scraping Blocks**: Backup strategies if IP gets blocked or rate limited
- **Data Validation**: Comprehensive validation to catch parsing errors early
- **Success Monitoring**: Track scraping success rates and data quality metrics

### 13.6. Future Automation Opportunities
- **AI-Assisted Manual Review**: LLM integration for ambiguous match verification
- **Real-time Monitoring**: Dashboard for pipeline health and match statistics
- **Notification System**: Alerts for manual review queue or pipeline failures
- **Performance Analytics**: Historical trending of athlete classifications
