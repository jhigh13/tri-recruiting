import json
from db.db_connection import get_db_session
from db.models import Runner
from rapidfuzz import process, fuzz

BATCH_FILE = "etl/data/batch1_complete.jsonl"

def update_runner_from_agent_output(agent_output: dict):
    """
    Update the runner's record in the database with AI agent output.
    Uses fuzzy matching for college name.
    """
    session = get_db_session()
    try:
        name = agent_output.get("name", "")
        college = agent_output.get("college", "")
        # Parse name
        parts = name.strip().split()
        if len(parts) < 2:
            print(f"Invalid name format: {name}")
            return
        first_name = parts[0].lower()
        last_name = " ".join(parts[1:]).lower()
        # Get all possible colleges for this runner name
        candidates = session.query(Runner).filter(
            Runner.first_name == first_name,
            Runner.last_name == last_name
        ).all()
        if not candidates:
            print(f"No runner found for {name}, {college}")
            return
        # Fuzzy match on college name
        college_names = [c.college_team for c in candidates]
        best_match = None
        best_score = 0
        for c in candidates:
            score = fuzz.token_set_ratio(college, c.college_team)
            if score > best_score:
                best_score = score
                best_match = c
        if best_score < 60:
            print(f"No good college match for {name}, {college}. Best: {best_match.college_team if best_match else None} (score {best_score})")
            return
        runner = best_match
        runner.high_school = agent_output.get("high_school")
        runner.hometown = agent_output.get("hometown")
        runner.swimmer = agent_output.get("swimmer")
        runner.score = agent_output.get("score")
        runner.match_confidence = agent_output.get("match_confidence")       
        session.commit()
        print(f"Updated runner: {runner.first_name} {runner.last_name}, {runner.college_team} (fuzzy score {best_score})")
    except Exception as e:
        session.rollback()
        print(f"Error updating runner: {e}")
    finally:
        session.close()

def main():
    with open(BATCH_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                result = json.loads(line)
                # Updated parsing for batch output structure
                agent_json = result["response"]["body"]["choices"][0]["message"]["content"]
                if isinstance(agent_json, str):
                    agent_output = json.loads(agent_json)
                else:
                    agent_output = agent_json
                update_runner_from_agent_output(agent_output)
            except Exception as e:
                print(f"Error processing line: {e}")

if __name__ == "__main__":
    main()