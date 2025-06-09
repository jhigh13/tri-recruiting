# USA Triathlon Talent ID Pipeline

## 1. Project Overview
We want to automate USA Triathlon’s process of identifying incoming college runners (800 m, 1500 m, 5000 m, 10000 m, 3000 m steeplechase for outdoors; 800 m, mile, 3000 m, 5000 m for indoors) and cross‐reference them against SwimCloud to discover which athletes have a swim background. If a match is found, we will classify each athlete’s swim/run performance against USA Triathlon’s time standards (World Leading, Internationally Ranked, Nationally Competitive, Development Potential) and output a color‐coded Excel or CSV.

**Change (2025-06-09):** Instead of scraping TFRRS directly, we now manually download and store each TFRRS HTML file in `etl/data/`, then batch process these files into the database. This approach avoids anti-bot issues and ensures we capture all athletes per event. After loading, we clean and normalize the data for analysis.

## 2. Data Sources

### 2.1. TFRRS (Track & Field Results Reporting System)
- **Data Source**: Manually saved HTML files from TFRRS, stored in `etl/data/` (one file per event/season)
- **Events**:  
  - Outdoor: 800 m, 1500 m, 3000 m steeplechase, 5000 m, 10000 m  
  - Indoor: 800 m, Mile, 3000 m, 5000 m  
- **Fields to extract**:  
  - Athlete name (first, last)  
  - Performance time (e.g., “2:01.23”)  
  - School/Team (e.g., “Stanford University”)  
  - Year (e.g., 2025)  
  - Gender (inferred from the HTML context)  
  - Event  
- **Volume**: Top 500 per event, both men and women, each season (Outdoor & Indoor). Later: consider Div II/III historical data.
- **Processing**: Batch process all HTML files in `etl/data/` to load athletes into the database.

### 2.2. SwimCloud (Public Website)
- **Search URL**: `https://www.swimcloud.com/swimmer/{swimmer_id}/` or search pages  
- **Fields to scrape**:  
  - Athlete name (first, last)  
  - Hometown (city, state)  
  - Age/Birth year (if available)  
  - Club/team affiliation (e.g., “California Aquatics”)  
  - List of swim times (LCM and YDS) by event (200 Free, 400/500 Free, 800/1000 Free, 1500/1650 Free)  
- **Challenges**:  
  - No official public API → use requests+BeautifulSoup or Selenium.  
  - Name collisions (e.g., multiple “Charles Hicks”) → require fuzzy matching + metadata validation.

### 2.3. USA Triathlon Time Standards
- **Source**: https://www.usatriathlon.org/our-community/elite-development/talent-id/time-standards  
- **Categories** (per gender/age):  
  - World Leading  
  - Internationally Ranked  
  - Nationally Competitive  
  - Development Potential  
- **Events**: Swim events (200 Free, 400/500 Free, 800/1000 Free, 1500/1650 Free); Run events (800 m, 1500 m, Mile, 3000 m, 5 k, 10 k); Bike power thresholds  
- **Data format**: We will store all cutoffs in a table or CSV for easy lookup.

## 3. Database Schema (Relational)

### 3.1. `runners` Table
| Column           | Type        | Description                             |
|------------------|-------------|-----------------------------------------|
| runner_id (PK)   | SERIAL/INT  | Unique identifier for this runner entry |
| first_name       | VARCHAR     | Lowercased, punctuation removed         |
| last_name        | VARCHAR     |                                         |
| college_team     | VARCHAR     | E.g., “Stanford University”             |
| event            | VARCHAR     | E.g., “800m_outdoor” or “Mile_indoor”   |
| performance_time | TIME (sec)  | Stored as total seconds, e.g. 121.23    |
| year             | INT         | E.g., 2025                              |
| gender           | CHAR(1)     | ‘M’ or ‘F’                              |
| hometown         | VARCHAR     | (Optional, if you enrich later)         |
| birth_year       | INT         | (Optional, if you enrich later)         |
| scrape_timestamp | TIMESTAMP   | When this row was inserted              |

### 3.2. `swimmers` Table
| Column           | Type        | Description                             |
|------------------|-------------|-----------------------------------------|
| swimmer_id (PK)  | SERIAL/INT  | Unique identifier for this swim entry   |
| first_name       | VARCHAR     | Lowercased, punctuation removed         |
| last_name        | VARCHAR     |                                         |
| hometown         | VARCHAR     | E.g., “Irvine, CA”                      |
| birth_year       | INT         | If available                            |
| swim_team        | VARCHAR     | E.g., “Golden West Swim Club”           |
| raw_swim_json    | JSONB       | (Optional) Full page scrape for reference|
| scrape_timestamp | TIMESTAMP   | When this row was inserted              |

### 3.3. `time_standards` Table
| Column             | Type        | Description                                   |
|--------------------|-------------|-----------------------------------------------|
| standard_id (PK)   | SERIAL/INT  | Unique identifier                             |
| gender             | CHAR(1)     | ‘M’ or ‘F’                                    |
| age_group          | VARCHAR     | “Junior” vs “Open” vs “Women’s” vs “Men’s” etc.|
| event              | VARCHAR     | E.g., “200_Free_LCM”, “5k_Run”                |
| category           | VARCHAR     | “World Leading” / “Intl Ranked” / “Nationally Competitive” / “Development” |
| cutoff_seconds     | NUMERIC     | All times normalized to seconds               |

### 3.4. `runner_swimmer_match` Table
| Column                    | Type        | Description                                                     |
|---------------------------|-------------|-----------------------------------------------------------------|
| match_id (PK)             | SERIAL/INT  | Unique match record                                             |
| runner_id (FK → runners)  | INT         | The runner being matched                                        |
| swimmer_id (FK → swimmers)| INT         | The candidate swimmer                                           |
| match_score               | NUMERIC     | Computed similarity score (0–100)                               |
| matched_on_fields         | TEXT[]      | Array of fields that matched (e.g., `['name','hometown']`)      |
| verification_status       | VARCHAR     | “auto_verified”, “manual_review”, or “no_match”                 |
| match_timestamp           | TIMESTAMP   | When this match was computed                                     |

### 3.5. `classification` Table
| Column                     | Type       | Description                                                             |
|----------------------------|------------|-------------------------------------------------------------------------|
| class_id (PK)              | SERIAL/INT | Unique classification record                                            |
| match_id (FK → runner_swimmer_match) | INT   | References the matched runner/swimmer                                    |
| standard_id (FK → time_standards)    | INT   | Which time standard was used                                              |
| category_assigned          | VARCHAR    | “Dark Green” / “Green” / “Yellow” / “Red”                                 |
| classification_timestamp   | TIMESTAMP  | When this classification was made                                         |

---

## 4. Matching Criteria (Detailed)

1. **Exact Match (Auto-Verified)**  
   - `runner.last_name = swimmer.last_name`  
   - AND `runner.first_name = swimmer.first_name`  
   - AND `runner.birth_year = swimmer.birth_year` (if available)  
   - AND (`runner.hometown = swimmer.hometown` OR `runner.college_team = swimmer.swim_team`)  
   - → `match_score = 100; verification_status = 'auto_verified'`

2. **Fuzzy-Name + Secondary Fields**  
   1. Compute `name_ratio = token_set_ratio(runner_full_name, swimmer_full_name)`  
      - If `name_ratio < 75`, **reject** immediately (no match).  
      - If `75 ≤ name_ratio < 90`, candidate for “manual_review.”  
      - If `name_ratio ≥ 90`, proceed to bonus scoring.  
   2. **Hometown Bonus**:  
      - If `runner.hometown = swimmer.hometown` exactly → `+20 points`  
      - Else if `token_set_ratio(runner.hometown, swimmer.hometown) ≥ 80` → `+10 points`  
   3. **Birth Year Bonus**:  
      - If `runner.birth_year = swimmer.birth_year` → `+15 points`  
      - If off by 1 year → `+5 points`  
   4. **School/Team Bonus**:  
      - If `runner.college_team` token‐matches `swimmer.swim_team` ≥ 80 → `+10 points`  
   5. **Total Score Calculation** (example weights):  
      ```
      total_score = name_ratio * 0.6 
                  + hometown_bonus 
                  + birth_year_bonus 
                  + school_bonus
      ```  
   6. **Final Decision**:  
      - If `total_score ≥ 90`: `auto_verified` → record into `runner_swimmer_match` with that status.  
      - If `70 ≤ total_score < 90`: `verification_status = "manual_review"`.  
      - If `total_score < 70`: `verification_status = "no_match"`.

3. **Manual Verification** (for those tagged “manual_review”)  
   - Export CSV of runner-swimmer pairs, with columns:  
     ```
     runner_id, runner_name, runner_college, swimmer_id, swimmer_name, swim_team, hometown, birth_year, total_score
     ```  
   - A human reviewer confirms or rejects. Update `runner_swimmer_match.verification_status` to “auto_verified” or “no_match” accordingly.

4. **Unmatched Runners**  
   - If no `verification_status="auto_verified"` or `"manual_review"` entry remains, mark runner as “No Swim Background” → classification = **Red**.

---

## 5. Classification Logic (Assigning Color Categories)

Once you have a verified `runner ↔ swimmer` pair, pull that swimmer’s best swim time(s) and compare against the appropriate `time_standards`. Example steps for a given runner:

1. Identify the runner’s age/gender bracket (“Junior Girls”, “Men’s Open”, etc.).  
2. For each swim event the runner competes in (e.g. 200 Free LCM):  
   - Retrieve best swim time for that event from the `swimmers` table.  
   - Look up `time_standards` row where `(gender = runner.gender, age_group = runner_age_group, event = “200_Free_LCM”)`.  
   - Compare `swim_time_seconds ≤ cutoff_seconds`.  
     - If yes, assign category = the matching `category` (World Leading, Internationally Ranked, etc.).  
3. If the athlete has multiple eligible swim events, use the **highest** tier (e.g., if they meet “Internationally Ranked” in 800 Free but only “Nationally Competitive” in 200 Free, assign “Internationally Ranked”).  
4. Map these to color codes:  
   - **World Leading → Dark Green**  
   - **Internationally Ranked → Green**  
   - **Nationally Competitive → Yellow**  
   - **Development Potential only (made the “Dev” cutoff but nothing higher) → Orange/Yellow–Green**  
   - **No Swim Profile or below Development Potential → Red**

At the end of this step, each runner (row in `runners`) will have either:
- A `classification` record pointing to a `time_standards` cutoff, or
- No matching swimmer → automatically classified as **Red**.

---

## 6. High-Level Workflow

1. **Seasonal Trigger (e.g., After Outdoor Track Ends)**  
   - Launch ETL job (e.g., an Airflow DAG, or a simple cron/powershell task).
   - Inputs: Year, Season (Outdoor/Indoor), Division (I only, for now).

2. **Step A: Process TFRRS HTML Files**  
   - For each HTML file in `etl/data/`, extract all athletes and load into the `runners` table.

3. **Step B: Scrape SwimCloud**  
   - For each row in `runners` where `verification_status` is NULL:  
     1. Build a search query URL (e.g., `https://www.swimcloud.com/search/?q={runner_full_name}`) or directly attempt known SwimCloud IDs if you have them.  
     2. Scrape candidate swimmers’ names, hometown, birth_year, swim_team, best swim times.  
     3. Normalize and INSERT/UPDATE into `swimmers` table (avoiding duplicates by checking if `first_name`, `last_name`, `birth_year`, and `swim_team` already exist).

4. **Step C: Name-Matching & Validation**  
   - Run the matching algorithm described in Section 2 on all new `(runner, swimmer)` pairs.  
   - Populate `runner_swimmer_match` with `match_score` and a provisional `verification_status`.  

5. **Step D: Manual Review**  
   - Generate a “manual_review.csv” of all pairs where `verification_status="manual_review"`.  
   - Human confirms or rejects. Update those rows accordingly.

6. **Step E: Classification**  
   - For every `runner` with `verification_status="auto_verified"`, fetch the corresponding swimmer’s best swim times.  
   - Compare against `time_standards` and insert a row into `classification`.  
   - For any runner without a verified swimmer, insert a classification row with category = “Red (No Swim Background)”.

7. **Step F: Output**  
   - Dump a final report as `top500_<event>_<year>_classification.csv` with columns:  
     ```
     runner_id, runner_name, event, school, year, swimmer_id (or NULL), 
     swim_team (or NULL), classification_category, classification_color, best_swim_event, best_swim_time
     ```  
   - Optionally, load that CSV into Power BI/Tableau for visual dashboards.

---

## 7. Matching Criteria Checklist


1. **Name Matching**  
   - **Exact (100 pts)**: `first_name`, `last_name` both match exactly after normalization.  
   - **Fuzzy**: `token_set_ratio ≥ 90 → “likely same”` / `80 ≤ ratio < 90 → “possible”` / `ratio < 75 → “no”`.

2. **Secondary Metadata**  
   - **Hometown**: exact match (+20) / fuzzy match ≥80 (+10)  
   - **Birth Year**: exact match (+15) / off by 1 year (+5)  
   - **School/Team**: token match ≥80 (+10)

3. **Score Weighting**  
   - `total_score = (name_ratio * 0.6) + hometown_bonus + birth_year_bonus + school_bonus`  
   - Auto‐approve if `total_score ≥ 90`.  
   - Manual review if `70 ≤ total_score < 90`.  
   - Reject if `< 70`.

4. **Manual Validation**  
   - Any pair scoring in the manual‐review band will be exported for human confirmation.

---

## 8. Next Steps


3. **Write the Detailed Spec**  
   - After finalizing the summary `.md` and schema, the next document will outline:  
     - Exact Python modules/packages to use (requests, BeautifulSoup, rapidfuzz, SQLAlchemy).  
     - PowerShell commands to install dependencies and schedule the job.  
     - Pseudocode for each pipeline step (scrape, match, classify).  
     - Example queries for pulling out “needs review” rows and classification reports.

4. **Implementation Planning**  
   - We’ll decide whether to containerize the scraper + classifier into a Docker image, or run it locally behind Task Scheduler.  
   - Design how to store credentials (if you later integrate a Google Custom Search API for “final name verification”), how to back up the database, and how to version‐control the code in GitHub.
