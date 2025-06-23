import json
from db.db_connection import get_db_session
from db.models import Runner

# Paste your system prompt here (from ai_agent.py)
SYSTEM_PROMPT = """Determine if a given NCAA runner has a previous swimming background.
Given a runner's profile: first name, last name, college team.
1. Build a query: 'name' + 'college team' + 'track and field'. Find runner's college profile. 
2. Create the query: 'name' + 'hometown' + 'SwimCloud'.
3. Search for possible matches on SwimCloud, a public swimming results website.
4. Use file search and the match.md file to calculate a match score for the runner. You must use the point values and criteria exactly as described in match.md. For each match, add up the points only from the criteria that are explicitly met. Do not round up, estimate, or invent new scoring rules
5. Respond ONLY with a valid JSON object:
{
"name": ...,
"college": ...,
"high_school": ...,
"hometown": ...,
"swimmer": ...,
"score": ...,
"match_confidence": ...
}
No extra text or formatting.

Example:
Input: Christian Jackson, Virginia Tech
Output:
{"name": "Christian Jackson", "college": "Virginia Tech", "high_school": "Colonial Forge", "hometown": "Stafford, VA", "swimmer": "No", "score": 50, "match_confidence": "High"}
"""

MODEL_NAME = "gpt-4.1-2"
OUTPUT_PATH = "etl/data/batch_processing.jsonl"

def main():
    session = get_db_session()
    runners = session.query(Runner).filter(Runner.swimmer == None).all()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for idx, runner in enumerate(runners):
            user_query = f"{runner.first_name} {runner.last_name}, {runner.college_team}"
            entry = {
                "custom_id": f"task-{idx}",
                "method": "POST",
                "url": "/chat/completions",
                "body": {
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_query}
                    ]
                }
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {len(runners)} tasks to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()