def llm_match_score(runner: dict, candidate: dict) -> tuple[int, str, str]:
    """
    Compute a match score using simple string/word overlap and reasoning.
    - Name: +60 if all words in runner name are in candidate name (case-insensitive, partial ok)
    - Hometown: +20 if exact, +10 if city or state matches
    - High school: +10 if high school in candidate matches runner (if available)
    - Swimming bio/news: +10 if candidate bio/news mentions 'swim', 'swimming', 'freestyle', etc.
    Returns (total_score, explanation, match_status)
    """
    score = 0
    explanation = []
    # Name check
    runner_name = f"{runner.get('first_name','')} {runner.get('last_name','')}".lower()
    candidate_name = (candidate.get('name') or '').lower()
    name_words = set(runner_name.split())
    if all(word in candidate_name for word in name_words):
        score += 60
        explanation.append("name_match=60")
    else:
        explanation.append("name_match=0 (not all name words found)")
    # Hometown check
    runner_ht = (runner.get('hometown') or '').lower()
    candidate_ht = (candidate.get('hometown') or '').lower()
    if runner_ht and candidate_ht:
        if runner_ht == candidate_ht:
            score += 20
            explanation.append("hometown_exact=20")
        elif any(part in candidate_ht for part in runner_ht.split(",")):
            score += 10
            explanation.append("hometown_partial=10")
        else:
            explanation.append("hometown=0")
    # High school check
    runner_hs = (runner.get('high_school') or '').lower()
    candidate_hs = (candidate.get('high_school') or '').lower()
    if runner_hs and candidate_hs and runner_hs in candidate_hs:
        score += 10
        explanation.append("high_school=10")
    # Swimming bio/news keyword
    bio = (candidate.get('bio') or '').lower()
    swim_keywords = ['swim', 'swimming', 'freestyle', 'backstroke', 'breaststroke', 'butterfly', 'im']
    if any(word in bio for word in swim_keywords):
        score += 10
        explanation.append("swim_bio=10")
    # Total
    explanation.append(f"total_score={score}")
    match_status = "Swimming Match" if score > 75 else "No Match"
    return score, "; ".join(explanation), match_status