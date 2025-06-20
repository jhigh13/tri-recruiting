# SwimCloud Match Scoring Logic for AI Agent

The following rules are used to determine if a runner and a SwimCloud profile are likely the same person (i.e., if the runner has a swimming background):

## Scoring Criteria

- **Name Match**: 
  - +60 points if all words in the runner's name (first and last) appear in swim cloud page (case-insensitive, partial matches allowed).
  - +50 points if some words in the runner's names appear in the swim cloud page 
  - 0 points if no words from the runner's name match on the swim cloud page
- **Hometown Match**:
  - +20 points if the runner's hometown closely matches the candidate's hometown (case-insensitive).
  - +10 points if either the city or state from the runner's hometown appears in the candidate's hometown.
- **High School Match**: +15 points
  - If the runner's high school appears in the candidate's high school field (case-insensitive).
- **Swimming Bio/News Keyword**: +5 points
  - If the candidate's bio or news contains any of these keywords: 'swim', 'swimming', 'freestyle', 'backstroke', 'breaststroke', 'butterfly', 'IM'.

## Decision Threshold

- **Return the score in the output.**
- **Return 'swimmer' = Yes if the total score is greater than 75, otherwise 'swimmer' = No.**
- **Always return the score, swimmer status, and a match_confidence field.**
- **Set match_confidence based on the quality and completeness of the data used to calculate the score, not the score itself:**
  - 'High' if the agent had strong, direct evidence for the match (e.g., exact name, hometown, and high school all matched, or multiple independent fields matched with high certainty), **or if no SwimCloud profile was found at all and there is clear evidence the runner does not have a swimming background**.
  - 'Medium' if the agent had partial or indirect evidence (e.g., only some fields matched, or some data was missing but the available evidence is reasonably convincing).
  - 'Low' if the agent had minimal data to work with, or the match is based on weak, ambiguous, or incomplete information (e.g., only a name match, or most fields were missing or uncertain).

## Example

If a runner named "Christian Jackson" from "Stafford, VA" with high school "Colonial Forge" is compared to a SwimCloud profile:
- If the name matches, +60
- If hometown matches exactly, +20
- If high school matches, +10
- If bio mentions "swimming", +5
- **Total: 100 → Swimming Match**
- **Return:**
  ```json
  {"name": "Christian Jackson", "college": "Virginia Tech", "high_school": "Colonial Forge", "hometown": "Stafford, VA", "swimmer": "Yes", "score": 100, "match_confidence": "High"}
  ```

If only the name matches, **Total: 60 → No Match**
- **Return:**
  ```json
  {"name": "Christian Jackson", "college": "Virginia Tech", "high_school": "Colonial Forge", "hometown": "Stafford, VA", "swimmer": "No", "score": 60, "match_confidence": "High"}
  ```

If no SwimCloud profile is found for the runner at all, and there is clear evidence the runner does not have a swimming background:
- **Return:**
  ```json
  {"name": "Christian Jackson", "college": "Virginia Tech", "high_school": "Colonial Forge", "hometown": "Stafford, VA", "swimmer": "No", "score": 0, "match_confidence": "High"}
  ```

---

The agent should sum the points for each matching criterion, return the score, swimmer status, and match_confidence, and use the threshold above to decide if the candidate is a swimming match.