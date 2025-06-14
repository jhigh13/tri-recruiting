import os, openai, json, textwrap
from dotenv import load_dotenv; load_dotenv()
openai.api_key       = os.getenv("AZURE_OPENAI_KEY")
openai.base_url      = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT           = os.getenv("AZURE_OPENAI_DEPLOYMENT")

def verify(runner: dict, candidate: dict, url: str) -> dict:
    system = "You are a triathlon talent ID assistant..."
    user = textwrap.dedent(f"""
      Runner:
        name: {runner['first_name']} {runner['last_name']}
        college_team: {runner.get('college_team')}

      Candidate Profile ({url}):
        birth_year: {candidateS['birth_year']}
        hometown: {candidate['hometown']}
        swim_team: {candidate['swim_team']}

      Are they the same person? Reply with JSON:
      {{ "decision": "ACCEPT|REJECT", "confidence": 0.0-1.0, "reasons": [...] }}
    """)
    resp = openai.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user}],
        temperature=0.2
    )
    return json.loads(resp.choices[0].message.content)
