# Implementation Plan for ai_agent_spec.md

- [x] Step 1: Configuration & Setup  
  - **Task**:  
    - Set up environment variables and required dependencies.  
    - Update `.env.example` with keys (AZURE_OPENAI_KEY, BING_SEARCH_KEY, etc.).  
    - Verify dependencies in `requirements.txt` (requests, beautifulsoup4, rapidfuzz, asyncio, SQLAlchemy).  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting/.env.example`: Add keys for Azure OpenAI and Bing Search API.  
    - `c:\Users\jhigh\Projects\tri-recruiting/requirements.txt`: Ensure required packages are listed.  
  - **Dependencies**: Environment variables, requirements file updates  
  - **User Intervention**: Confirm keys and dependency versions.

- [x] Step 2: Create AI Agent Module  
  - **Task**:  
    - Create a new module at `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py` to encapsulate AI agent logic.  
    - Define a main function (e.g., `process_all_runners`) for asynchronous processing of runner records.  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      # ...existing module setup...
      async def process_all_runners() -> None:
          # Retrieve runner records from the DB
          # Process each runner asynchronously (using asyncio.gather)
          pass
      ```
  - **Dependencies**: asyncio, SQLAlchemy, logging  
  - **User Intervention**: Review module structure before integration.

- [x] Step 3: Implement Runner Retrieval & Query Generation  
  - **Task**:  
    - Develop helper functions: one to retrieve runners from the database, and one to build search queries using runner attributes (first name, last name, optional college/team).  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      def get_runners() -> List[Dict]:
          # ...retrieve runners from DB...
          pass

      def build_search_query(runner: Dict) -> str:
          # Build the query using runner['first_name'], runner['last_name']
          # Optionally include runner.get('college_team') or runner.get('hometown')
          return f"{runner['first_name']} {runner['last_name']} swim profile"
      ```
  - **Dependencies**: DB connection module  
  - **User Intervention**: Validate query format against expected web search API input.

- [x] Step 4: Integrate Asynchronous Bing Search API  
  - **Task**:  
    - Develop an asynchronous function `bing_search_async(query: str) -> List[Dict]` to query the Bing Search API with caching.  
    - Implement region/language filtering.  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      async def bing_search_async(query: str) -> List[Dict]:
          # Pseudocode:
          # 1. Check in-memory cache for the query result.
          # 2. If not cached, perform an async HTTP GET request to Bing Search API with headers.
          # 3. Parse JSON response, store in cache, and return results.
          pass
      ```
  - **Dependencies**: asyncio, requests (or aiohttp for async support), caching mechanism  
  - **User Intervention**: Decide on caching duration and strategy.

- [x] Step 5: Candidate Page Parsing  
  - **Task**:  
    - Create a function `get_and_parse_candidate(url: str) -> Dict` that performs an HTTP GET with polite scraping.  
    - Use BeautifulSoup to extract SwimCloud page details (name, hometown, birth_year, swim times, swim team).  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      def get_and_parse_candidate(url: str) -> Dict:
          # 1. Send an HTTP GET request with custom User-Agent and timeout.
          # 2. Use time.sleep(1-2) for politeness.
          # 3. Parse the response HTML with BeautifulSoup.
          # 4. Extract candidate details and return a dictionary.
          pass
      ```
  - **Dependencies**: requests, BeautifulSoup, time  
  - **User Intervention**: Validate parsing selectors using example SwimCloud pages.

- [x] Step 6: Implement Match Scoring Function  
  - **Task**:  
    - Write a function `compute_match_score(runner: Dict, candidate: Dict) -> Tuple[int, str]` that computes similarity scores using rapidfuzz.  
    - Incorporate bonus points for hometown, birth_year, and team matching, and generate an explanation text.  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      def compute_match_score(runner: Dict, candidate: Dict) -> Tuple[int, str]:
          # 1. Compute name_ratio using rapidfuzz.token_set_ratio.
          # 2. Determine bonuses based on matching hometown, birth_year, and team.
          # 3. Calculate total_score = (name_ratio * 0.6) + bonuses.
          # 4. Create an explanation string detailing each component.
          return total_score, explanation
      ```
  - **Dependencies**: rapidfuzz, logging  
  - **User Intervention**: Confirm scoring thresholds and bonus values.

- [x] Step 7: Aggregate Results & Update Database  
  - **Task**:  
    - For each runner, iterate through candidate matches to determine best and potential manual review candidates.  
    - Write results to the `runner_swimmer_match` table by upserting match details including score, status, and explanation.  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      def update_match_record(runner_id: int, match_details: Dict) -> None:
          # Use SQLAlchemy's session.merge() to update runner_swimmer_match table.
          # Commit changes and log the update.
          pass
      ```
  - **Dependencies**: SQLAlchemy, db_connection  
  - **User Intervention**: Review database schema alignment with match output.

- [x] Step 8: Manual Review CSV Generation & Detailed Logging  
  - **Task**:  
    - Implement functionality to export a CSV containing all manual review candidates with columns: runner_id, first_name, last_name, match_score, verification_status, and match_details (including SwimCloud profile links).  
    - Ensure detailed logs are captured at each processing step for troubleshooting.  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\etl\ai_agent.py`:  
      ```python
      def export_manual_review(matches: List[Dict]) -> None:
          # Write manual review CSV with required columns.
          pass
      ```
    - Optionally, create/update a logging file at: `c:\Users\jhigh\Projects\tri-recruiting\logs/ai_agent.log`
  - **Dependencies**: csv module, logging  
  - **User Intervention**: Confirm CSV format and log verbosity.

- [ ] Step 9: Testing & Validation  
  - **Task**:  
    - Develop unit tests and integration tests for the AI Agent module.  
    - Use pytest to mock external HTTP calls (Bing API and SwimCloud GET requests) and validate each function (runner retrieval, query generation, async search, candidate parsing, scoring, and DB updates).  
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting\tests\test_ai_agent.py`:  
      ```python
      # Pseudocode tests:
      # - Test get_runners() returns expected records.
      # - Test build_search_query() with sample runner data.
      # - Test bing_search_async() for caching behavior.
      # - Test compute_match_score() against known inputs.
      # - Test overall process_all_runners() integration.
      ```
  - **Dependencies**: pytest, requests-mock (or similar)
  - **User Intervention**: Review test coverage requirements.

- [ ] Step 10: Final Review & Documentation  
  - **Task**:  
    - Document usage instructions for the AI Agent module in the README or a separate docs file.  
    - Update the ai_agent_spec.md with any final clarifications from implementation.  
    - Request user review of final logs and CSV outputs to ensure accessibility and clarity.
  - **Files**:  
    - `c:\Users\jhigh\Projects\tri-recruiting/README.md`: Add a section on AI Agent usage.  
    - `c:\Users\jhigh\Projects\tri-recruiting\docs\ai_agent_spec.md`: Incorporate final deployment notes.
  - **Dependencies**: Documentation tools  
  - **User Intervention**: Final approval before production rollout.

**Note:** Do not start implementation until you have reviewed and approved this plan.
