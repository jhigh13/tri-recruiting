from rapidfuzz.fuzz import token_set_ratio

# Scoring constants
MATCH_THRESHOLD = 90
MANUAL_THRESHOLD = 70
HOMETOWN_EXACT_BONUS = 20
HOMETOWN_FUZZY_BONUS = 10
BIRTH_YEAR_EXACT_BONUS = 15
BIRTH_YEAR_OFF_BY_ONE_BONUS = 5
SCHOOL_FUZZY_BONUS = 10


def compute_match_score(runner: Dict, candidate: Dict) -> tuple[int, str]:
    """
    Compute a match score between a runner and a SwimCloud candidate.
    Returns (total_score, explanation).
    """
    explanation_parts: list[str] = []
    runner_name = f"{runner['first_name']} {runner['last_name']}"
    candidate_name = candidate.get('name', '')
    name_ratio = token_set_ratio(runner_name, candidate_name)
    explanation_parts.append(f"name_ratio={name_ratio}")

    # Reject if name_ratio < 75
    if name_ratio < 75:
        explanation = f"Name ratio {name_ratio} below 75: no match."
        return 0, explanation

    # Hometown bonus
    hometown_bonus = 0
    r_ht = runner.get('hometown') or ''
    c_ht = candidate.get('hometown') or ''
    if r_ht and c_ht:
        if r_ht.lower() == c_ht.lower():
            hometown_bonus = HOMETOWN_EXACT_BONUS
            explanation_parts.append(f"hometown_exact_bonus={HOMETOWN_EXACT_BONUS}")
        else:
            ht_ratio = token_set_ratio(r_ht, c_ht)
            if ht_ratio >= 80:
                hometown_bonus = HOMETOWN_FUZZY_BONUS
                explanation_parts.append(f"hometown_fuzzy_bonus={HOMETOWN_FUZZY_BONUS}")
    
    # Birth year bonus
    birth_bonus = 0
    r_by = runner.get('birth_year')
    c_by = candidate.get('birth_year')
    if r_by and c_by:
        if r_by == c_by:
            birth_bonus = BIRTH_YEAR_EXACT_BONUS
            explanation_parts.append(f"birth_year_exact_bonus={BIRTH_YEAR_EXACT_BONUS}")
        elif abs(r_by - c_by) == 1:
            birth_bonus = BIRTH_YEAR_OFF_BY_ONE_BONUS
            explanation_parts.append(f"birth_year_off_by_one_bonus={BIRTH_YEAR_OFF_BY_ONE_BONUS}")

    # School/team bonus
    school_bonus = 0
    r_team = runner.get('college_team') or ''
    c_team = candidate.get('swim_team') or ''
    if r_team and c_team:
        team_ratio = token_set_ratio(r_team, c_team)
        if team_ratio >= 80:
            school_bonus = SCHOOL_FUZZY_BONUS
            explanation_parts.append(f"school_fuzzy_bonus={SCHOOL_FUZZY_BONUS}")

    # Total score
    total_score = int(name_ratio * .6 + hometown_bonus + birth_bonus + school_bonus)
    explanation_parts.append(f"total_score={total_score}")
    explanation = "; ".join(explanation_parts)
    return total_score, explanation