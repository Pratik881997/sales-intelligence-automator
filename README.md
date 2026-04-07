# Sales Intelligence Automator

Sales research prototype that:
1. accepts lead input (URL/domain/company string),
2. discovers and crawls lead websites,
3. summarizes findings with a local LLM (Ollama),
4. outputs structured sales briefs for an IT-services sales team.

---

## Architecture Overview

### End-to-end flow

1. **Lead ingestion**  
   Parse leads from text area or CSV (`leads` column).

2. **Input routing**
   - **Direct website input** (`https://...`, `http://...`, `example.com`)  
     -> open directly in Selenium and crawl.
   - **String input** (company + city, etc.)  
     -> search Google in Selenium up to 3 result pages, parse **organic only**, pick most relevant official site, then crawl.

3. **Website crawl**
   - Primary path: Selenium loads landing page and discovered internal pages (`about`, `services`, `contact`).
   - Fallback path: if Selenium returns blocked/empty landing content, use `requests` + BeautifulSoup to fetch and extract text from landing/internal pages.

4. **LLM analysis (Ollama)**
   - For string search results: pick the official domain from organic candidates.
   - For crawled content: produce structured JSON brief:
     - company overview
     - services
     - target audience
     - contact details
     - B2B qualification
     - IT-focused sales questions

5. **Output**
   - Streamlit table + detailed expansions.
   - Export JSON/CSV.
   - Persist to `output/results.json`.

---

## Problem Handling & Solutions

### 1) Website not accessible / blocked / DNS errors

**Problem**
- Selenium may fail with errors like `ERR_NAME_NOT_RESOLVED`.
- Some sites return blocked pages or empty HTML to browser automation.

**Solution implemented**
- Catch Selenium crawl exceptions and continue flow.
- Detect DNS resolution failures and return clean status (`DNS_UNRESOLVED`) instead of stacktrace noise.
- Add `requests` fallback crawler with URL variants:
  - `https://host`
  - `https://www.host`
  - `http://host`
  - `http://www.host`
- If Selenium fails but requests succeeds, summary is still generated and tagged with `requests_fallback` in `research_notes`.

### 2) Sponsored Google results polluting discovery

**Problem**
- Ads/sponsored SERP blocks can be mistaken for organic business websites.

**Solution implemented**
- Strip known sponsored containers from SERP HTML (`#tads`, `#bottomads`, etc.).
- Parse only organic result structures with primary + fallback parsers.
- Reject non-official third-party domains (directories/social) in URL plausibility checks.
- LLM selects best official result; heuristic fallback applies if LLM is uncertain.

### 3) Generic sales questions

**Problem**
- LLM sometimes returns generic sales questions not aligned to IT-services positioning.

**Solution implemented**
- Prompt explicitly asks for IT-services consultative questions.
- Post-processing enforces exactly 3 questions.
- Generic questions are replaced with domain-aware IT discovery questions (automation, integrations, disconnected systems, operational efficiency).

---

## Tools & Libraries Used

### Core application
- `streamlit` - web UI
- `pandas` - tabular display/export
- `pydantic` - structured output models

### Browser automation & crawling
- `selenium` - browser automation (Google search + site navigation)
- `webdriver-manager` - auto-manages ChromeDriver based on installed Chrome
- `beautifulsoup4` - HTML parsing and text extraction
- `requests` - fallback HTTP fetching when Selenium is blocked

### LLM
- `requests` -> Ollama HTTP API (`/api/generate`) for:
  - official-site selection from organic SERP rows
  - structured company summary generation

### Utilities & testing
- `python-dotenv` - local environment loading
- `pytest` - unit tests

---

## Key Implementation Snippets

### Input routing (direct URL vs string search)
```python
direct = resolve_direct_url(lead)
if direct:
    chosen = direct
else:
    for page in range(3):
        search_google_query(driver, query, page)
        html = fetch_organic_results_html(driver)
        organic = parse_organic_comprehensive(html)
        chosen = pick_relevant_url(lead, organic, config.model_name)
        if chosen:
            break
```

### Sponsored-result filtering and organic parsing
```python
for sel in ("#tads", "#tadsb", "#bottomads", "#tvcap", "#taw", ".commercial-unit"):
    for node in soup.select(sel):
        node.decompose()
```

### Selenium -> requests fallback on blocked/empty crawl
```python
texts, pages = crawl_company_pages(driver, chosen)
landing = (texts.get("landing") or "").strip()
if not landing:
    req_texts, req_pages = crawl_company_pages_requests(chosen)
    if (req_texts.get("landing") or "").strip():
        texts, pages = req_texts, req_pages
```

### DNS error handling
```python
if "err_name_not_resolved" in selenium_error.lower():
    return SalesBrief(
        lead_input=lead,
        resolved_url=chosen,
        rationale="Domain could not be resolved (DNS lookup failed).",
        research_notes="DNS_UNRESOLVED",
    )
```

---

## Setup

```bash
env\Scripts\python -m pip install -r requirements.txt
```

Prerequisites:
- Google Chrome installed
- Ollama running locally with a pulled model (`mistral:latest`, `gemma3:4b`, or `gemma4:latest`)

---

## Run

### Streamlit UI
```bash
env\Scripts\python -m streamlit run app.py
```

### Batch mode
```bash
env\Scripts\python run_batch.py leads.csv mistral:latest
```

Output is written to `output/results.json`.

---

## Tests

```bash
env\Scripts\python -m pytest -q
```

Tests cover parsing, routing utilities, organic-result extraction, and JSON handling logic (without requiring live Google/Ollama calls).

---

## Project Structure

- `app.py` - Streamlit frontend
- `run_batch.py` - CLI batch execution
- `sales_intel/pipeline.py` - orchestration and fallback control flow
- `sales_intel/driver_factory.py` - ChromeDriver setup via webdriver-manager
- `sales_intel/selenium_google.py` - Google search navigation
- `sales_intel/google_organic.py` - sponsored stripping + organic parsing
- `sales_intel/site_crawl.py` - Selenium crawl + requests fallback crawl
- `sales_intel/llm.py` - Ollama interaction and IT-sales question enforcement
- `sales_intel/models.py` - typed brief schema
- `tests/` - unit tests
