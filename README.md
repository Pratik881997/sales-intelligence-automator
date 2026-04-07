# Sales Intelligence Automator

### Input routing

| Input type | What happens |
|------------|----------------|
| **Website** | `http(s)://…` or **bare domain** without spaces (e.g. `example.com`) → **no Google**. Selenium opens that URL directly, then crawls landing + About / Contact / Services when linked, then **Ollama** summarizes. |
| **String** (company name, city, etc.) | **Google in Chrome**: page 1 uses **google.com** and the real search box; pages 2–3 use `search?q=…&start=10` / `20`. **Sponsored** blocks are stripped from HTML; only **organic** results are parsed (primary + fallback parsers). **Ollama** picks the best official site; if the model is unsure, a **keyword heuristic** picks from organic results. Up to **3 pages**; if nothing usable → **not found** (`NOT_FOUND_IN_SEARCH`). Then same **crawl + summarize** as above. |

## Requirements

- **Google Chrome** installed (version matched automatically via **webdriver-manager**).
- **Ollama** running locally with a model pulled (e.g. `mistral:latest`).

## Setup

```bash
env\Scripts\python -m pip install -r requirements.txt
```

## Run (UI)

```bash
env\Scripts\python -m streamlit run app.py
```

## Run (batch CLI)

```bash
env\Scripts\python run_batch.py leads.csv mistral:latest
```

Writes `output/results.json`.

## Tests

```bash
env\Scripts\python -m pytest -q
```

Unit tests cover HTML parsing and text extraction (no live Google/Ollama calls).

## Project layout

- `sales_intel/driver_factory.py` — Chrome via `ChromeDriverManager`
- `sales_intel/selenium_google.py` — navigate Google result pages
- `sales_intel/google_organic.py` — BS4: organic-only results
- `sales_intel/site_crawl.py` — BS4 text extraction after Selenium navigation
- `sales_intel/llm.py` — Ollama: URL choice + final summary JSON
- `sales_intel/pipeline.py` — orchestration (sequential, one browser per lead)

## Notes

- Google’s HTML changes occasionally; organic selectors may need tweaks if results come back empty.
- Running many leads runs **one Chrome session per lead** for stability.
- For debugging, disable **Headless** in the Streamlit sidebar to watch the browser.
