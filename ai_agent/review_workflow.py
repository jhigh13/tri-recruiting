from .search import web_search
from .fetch  import fetch_html
from .parser import parse_swimcloud
from .verifier import verify

def review_runner(r):
    query = f"{r.first_name} {r.last_name} SwimCloud"
    urls  = web_search(query)
    if not urls:
        return {"decision":"NO_PROFILE","confidence":0,"reasons":["no search hits"]}
    html = fetch_html(urls[0])
    candidate = parse_swimcloud(html)
    return verify(r, candidate, urls[0])
