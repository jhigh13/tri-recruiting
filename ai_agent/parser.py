from bs4 import BeautifulSoup

def parse_swimcloud(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    data = {
        "birth_year": soup.select_one(".birth-year") and
                      soup.select_one(".birth-year").text.strip(),
        "hometown":   soup.select_one(".hometown") and
                      soup.select_one(".hometown").text.strip(),
        "swim_team":  soup.select_one(".swim-team") and
                      soup.select_one(".swim-team").text.strip()
    }
    return data
