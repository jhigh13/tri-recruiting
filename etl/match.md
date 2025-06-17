# SwimCloud Match Scoring Logic for AI Agent

The following rules are used to determine if a runner and a SwimCloud profile are likely the same person (i.e., if the runner has a swimming background):

## Scoring Criteria

- **Name Match**: +60 points
  - If all words in the runner's name (first and last) appear in the candidate's name (case-insensitive, partial matches allowed).
- **Hometown Match**:
  - +20 points if the runner's hometown exactly matches the candidate's hometown (case-insensitive).
  - +10 points if either the city or state from the runner's hometown appears in the candidate's hometown.
- **High School Match**: +10 points
  - If the runner's high school appears in the candidate's high school field (case-insensitive).
- **Swimming Bio/News Keyword**: +10 points
  - If the candidate's bio or news contains any of these keywords: 'swim', 'swimming', 'freestyle', 'backstroke', 'breaststroke', 'butterfly', 'IM'.

## Decision Threshold

- **Swimming Match**: If the total score is greater than 75.
- **No Match**: If the total score is 75 or below.

## Example

If a runner named "Christian Jackson" from "Stafford, VA" with high school "Colonial Forge" is compared to a SwimCloud profile:
- If the name matches, +60
- If hometown matches exactly, +20
- If high school matches, +10
- If bio mentions "swimming", +10
- **Total: 100 → Swimming Match**

If only the name matches, **Total: 60 → No Match**

---

The agent should sum the points for each matching criterion and use the threshold above to decide if the candidate is a swimming match.