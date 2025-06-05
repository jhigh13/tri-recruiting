# Copilot Context Examples

Include the following snippets in your repository to guide GitHub Copilot when writing code for the Triathlon Talent ID pipeline.

---

## 1. `config/events.yaml`

```yaml
# Sample mapping (event-id → canonical event name)
12: 800m_outdoor
20: 1500m_outdoor
41: 5000m_outdoor
58: 10000m_outdoor
73: 3000m_steeple_outdoor
5: 800m_indoor
8: mile_indoor
15: 3000m_indoor
23: 5000m_indoor
```

---

## 2. Inline Comment in `etl/scrape_tfrrs.py`

```html
<!-- Example <tr> snippet from TFRRS top-500 800m row -->
<tr>
  <td class="rank">1</td>
  <td class="athlete">
    <a href="/athletes/12345/John_Doe">John Doe</a>
  </td>
  <td class="school">Stanford University</td>
  <td class="performance">1:48.23</td>
  <td class="year">2025</td>
</tr>
```

---

## 3. Inline Comment in `etl/scrape_swimcloud.py`

```html
<!-- Minimal SwimCloud HTML snippet showing hometown, birth-year, best-times table header -->
<div class="profile-header">
  <h1>Jane Smith</h1>
  <div class="profile-details">
    <span class="hometown">Irvine, CA</span>
    <span class="birth-year">2003</span>
    <span class="swim-team">Irvine Novaquatics</span>
  </div>
</div>
<table class="times-table">
  <tr>
    <th>Event</th>
    <th>Time</th>
    <th>Date</th>
  </tr>
  <tr>
    <td>200 Free</td>
    <td>2:01.50</td>
    <td>2024-07-15</td>
  </tr>
</table>
```

---

## 4. `data/time_standards.csv` (First 3 Lines)

```csv
gender,event,category,cutoff_seconds,color_label
M,200_Free_LCM,World_Leading,109.50,Dark_Green
M,200_Free_LCM,Intl_Ranked,113.00,Green
M,200_Free_LCM,Nationally_Competitive,116.50,Yellow
```

---

## 5. Docstring in `etl/data_cleaning.py`

```python
def time_to_seconds(time_str: str) -> float:
    """
    Convert a time string to total seconds.

    Examples:
      "1:48.23" → 108.23
      "13:45.55" → 825.55
      "9:01.12" → 541.12
    """
    # Implementation goes here
```

---

## 6. Docstring in `matcher.py`

```python
"""
Compute match_score between runner and swimmer records.

Scoring formula:
    total_score = (name_ratio * 0.6) + hometown_bonus + birth_year_bonus + school_bonus

Thresholds:
  - Auto-verify if total_score ≥ 90
  - Manual review if 70 ≤ total_score < 90
  - Reject if total_score < 70
"""
```

---

## 7. `.env.example`

```bash
# Rename to .env and fill in your own keys
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
DATABASE_URL="postgresql://user:pass@localhost:5432/triathlon"
CHROMEDRIVER_PATH="C:/WebDrivers/chromedriver.exe"
```

---

## 8. Example Tests in `tests/test_time_conversion.py`

```python
import pytest
from etl.data_cleaning import time_to_seconds

# Failing case (before implementing conversion)
# assert time_to_seconds("1:48.23") == 108.23
# assert time_to_seconds("13:45.55") == 825.55
# assert time_to_seconds("9:01.12") == 541.12

# After implementing, these should pass:

def test_time_conversion_minutes_seconds():
    assert time_to_seconds("1:48.23") == pytest.approx(108.23)
    assert time_to_seconds("13:45.55") == pytest.approx(825.55)

def test_time_conversion_seconds_only():
    assert time_to_seconds("9:01.12") == pytest.approx(541.12)
```

---

## 9. README Pipeline Diagram (Top of `README.md`)

```text
Pipeline Overview:

1. Scrape TFRRS for top-500 athletes per event
2. Scrape SwimCloud for candidate swimmer profiles
3. Match runners to swimmers (fuzzy + metadata)
4. Manual review for ambiguous matches
5. Classify swim/run performance against standards
6. Generate CSV/Excel reports
```

---

## 10. ASCII ER Diagram in `db/models.py`

```python
# Runner, Swimmer, and Match Relationships:
#
#    +-----------------+       +--------------------+       +--------------------+
#    |     runners     |       |       swimmers     |       | runner_swimmer_match |
#    |-----------------|       |--------------------|       |----------------------|
#    | runner_id (PK)  | 1   * | swimmer_id (PK)    |       | match_id (PK)       |
#    | first_name      |-------| first_name         |       | runner_id (FK)      |
#    | last_name       |       | last_name          |       | swimmer_id (FK)     |
#    | college_team    |       | hometown           |       | match_score         |
#    | event           |       | birth_year         |       | matched_on_fields   |
#    | performance     |       | swim_team          |       | verification_status |
#    | year            |       +--------------------+       +----------------------+
#    | gender          |
#    +-----------------+
```
