import os, requests
from urllib.parse import urlencode
from dotenv import load_dotenv; load_dotenv()

KEY = os.getenv("AZURE_WEBSEARCH_KEY")
ENDPOINT = os.getenv("AZURE_WEBSEARCH_ENDPOINT")

def web_search(query: str, top: int = 5):
    params = urlencode({"q": query, "count": top})
    url = f"{ENDPOINT}/bing/v7.0/search?{params}"
    headers = {"Ocp-Apim-Subscription-Key": KEY}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return [d["url"] for d in r.json()["webPages"]["value"]]


