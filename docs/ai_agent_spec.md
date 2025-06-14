# AI Agent Detailed Specification

## 1. Overview
The AI Agent automates determining if a given NCAA Division I runner has a swim background by:
- Querying web resources (using Bing Search API)
- Parsing SwimCloud pages using HTTP GET and BeautifulSoup
- Comparing extracted data with runner information from the database
- Calculating a match score via fuzzy matching and bonus criteria
- Flagging uncertain matches for manual review

## 2. Architecture & Deployment
- **Language/Runtime:** Python 3.11+  
- **Hosting:** Deployed on Azure (via Azure Functions, Container Instances, or App Service)  
- **Integration:**  
  - Azure OpenAI for natural language tasks (query refinement and explanation generation)  
  - Bing Search API for web searches  
  - Polite HTTP GET requests (using requests and BeautifulSoup)
- **Asynchronous Processing:**  
  - Process runner records in asynchronous batches for scalability

## 3. Data Flow & Input/Output
- **Input:** Runner records (fields include first_name, last_name, college_team, gender, hometown, and birth_year) pulled from the database  
- **Processing:**  
  1. **Search Query Construction:**  
     - Build first query using runner first and last name swimcloud. Additional query can be enriched with contextual clues (college, hometown)  
     - Optionally refine using Azure OpenAI  
  2. **Web Search:**  
     - Execute asynchronous Bing Search API calls with region/language filtering  
     - Cache responses to avoid repeated queries  
  3. **Candidate Filtering & Parsing:**  
     - Filter results to include only SwimCloud URLs  
     - Parse candidate pages, extracting name, hometown, age/birth_year, swim times, and affiliated swim team  
  4. **Match Scoring:**  
     - Compute `name_ratio` using rapidfuzz  
     - Add bonuses for matching hometown, birth_year, and team/college  
     - Compute:  
       ```
       total_score = (name_ratio * 0.6) + hometown_bonus + birth_year_bonus + school_bonus
       ```  
  5. **Decision Making:**  
     - If `total_score ≥ 90`: auto-verify the match  
     - If `70 ≤ total_score < 90`: flag for manual review  
     - If multiple high-scoring matches exist, return the best match for auto-verification and include all candidates in manual review export  
  6. **Output:**  
     - Update or insert records into the `runner_swimmer_match` table with details of the match, score, and explanation  
     - Produce a manual review CSV with runner_id, match explanations, and candidate details if needed

## 4. Detailed Workflow
1. **Runner Retrieval:**  
   - Fetch runner records (single or batch) from the database.
2. **Search Query Generation:**  
   - Construct queries using runner attributes and context.
   - Optionally use Azure OpenAI to refine queries.
3. **Asynchronous Bing Search:**  
   - Dispatch search requests with filters for region/language.
   - Cache results for reduced latency.
4. **Candidate Parsing:**  
   - For each candidate SwimCloud URL, perform HTTP GET requests with proper rate-limiting and logging.
   - Parse page content with BeautifulSoup to extract key data.
5. **Match Scoring & Validation:**  
   - Use rapidfuzz.token_set_ratio to compute name matching and bonus points.
   - Generate a textual explanation for each score.
6. **Result Aggregation & Decision:**  
   - Determine verification_status based on the total match score.
   - If multiple high-scoring results exist, select the best match but include all in the manual review output.
7. **Record Updates:**  
   - Upsert matching data into `runner_swimmer_match`.
   - Log detailed debugging information for each stage.

## 5. Tools & Libraries
- **HTTP & HTML:** requests, BeautifulSoup  
- **Fuzzy Matching:** rapidfuzz.token_set_ratio  
- **Database:** SQLAlchemy, with session.merge() for upserts  
- **Azure Services:** Azure OpenAI API, Bing Search API  
- **Async Utilities:** asyncio or concurrent.futures for asynchronous processing  
- **Caching:** In-memory or Redis caching for search results

## 6. Deployment & Integration Considerations
- Package the agent as a module in the ETL pipeline.
- Configure deployment via environment variables (`AZURE_OPENAI_KEY`, `BING_SEARCH_KEY`, etc.)
- Ensure robust error handling, logging, and adherence to rate limits.
- Schedule processing via Azure Functions or a PowerShell-based scheduler.

## 7. Pseudocode Example
```
def process_runner(runner: Dict) -> Dict:
    # Build search query using runner details
    query = f"{runner['first_name']} {runner['last_name']} {runner.get('college_team', '')} swim profile"
    
    # Execute asynchronous Bing Search API call (with caching)
    search_results = bing_search_async(query)
    
    # Filter results to include SwimCloud URLs
    candidate_urls = [r['url'] for r in search_results if "swimcloud.com" in r['url']]
    
    candidates = []
    for url in candidate_urls:
        page_html = get_page(url)
        data = parse_swimcloud_page(page_html)
        candidates.append(data)
    
    best_match = None
    for candidate in candidates:
        score, explanation = compute_match_score(runner, candidate)
        if best_match is None or score > best_match['score']:
            best_match = {'score': score, 'explanation': explanation, 'candidate': candidate}
    
    if best_match:
        if best_match['score'] >= 90:
            status = "auto_verified"
        elif best_match['score'] >= 70:
            status = "manual_review"
        else:
            status = "no_match"
    else:
        status = "no_match"
    
    return {
        'runner_id': runner['runner_id'],
        'match_score': best_match['score'] if best_match else 0,
        'verification_status': status,
        'match_details': best_match
    }
```

## 8. Open Questions & Clarifications
- Should the agent process runners synchronously or strictly via asynchronous batches?
- Would you like additional query filters (e.g., language, location) to narrow search responses?
- Are there preferences for caching duration or strategy for Bing Search results?
- How should detailed logs be archived or forwarded for later debugging?
- In cases of multiple high-scoring candidates, do you want them all returned or only the one with the highest score?

- For search query construction, would you like to include additional filtering criteria such as region or language?
- The initial search query will focus on the runner's name. Additional filtering criteria can be added later if needed. I envision the agent starting with a basic query like Christian Jackson swimcloud

- Is caching search results acceptable to minimize repeated API calls and latency?
Yes, caching search results is acceptable and can significantly improve performance by reducing redundant API calls.

- Do you have specific preferences on the format/structure of manual review output CSVs?
Yes, the manual review output CSVs should include the following columns: runner_id, first_name, last_name, match_score, verification_status, and match_details.

- How should the agent handle cases when multiple high-scoring matches are found—should it return the best match or all potential matches for manual review?
The agent should return all potential matches for manual review. Ideally give links to the SwimCloud profiles for each match, so the user can easily access them.

- Would you like the agent to log detailed debugging information for each step, or limit output to summary logs?
Yes, the agent should log detailed debugging information for each step to facilitate troubleshooting and performance monitoring.

