import requests, random, time
UA_LIST = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64)...", "..."]

def fetch_html(url: str) -> str:
    headers = {"User-Agent": random.choice(UA_LIST)}
    time.sleep(1)  # polite delay
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text
