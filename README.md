# CityRisk Scout

AI-powered city risk assessment using open-source intelligence.
Scrapes public news and humanitarian reports with **Scrapling**, then uses an **LLM** (Anthropic or any OpenAI-compatible API) to generate a structured risk report.

## Architecture

```
User (web form)
  → FastAPI backend  (back/)
    → Scrapling scraper (concurrent, 4 sources)
      ├── ReliefWeb API      (UN OCHA humanitarian/disaster/crisis reports)
      ├── Reddit JSON API    (public search, no auth)
      ├── Google News RSS    (latest headlines)
      └── Wikipedia REST API (city background context)
    → LLM API (structured JSON analysis)
  → Risk Report (5 categories, score 0-100, sources)
```

## Project structure

```
city-risk-scout/
├── back/           # FastAPI app, scraper, analyzer, models
├── front/          # HTML, CSS, JavaScript (served as static files)
├── tests/          # Unit tests (pytest)
├── .env.example    # Environment variable template
└── pyproject.toml
```

## Risk categories assessed

| Category | Description |
|---|---|
| Political stability | Elections, coups, sanctions, governance |
| Civil unrest & crime | Protests, violence, crime rates |
| Natural disaster & environment | Earthquakes, floods, wildfires, pollution |
| Health & humanitarian | Epidemics, displacement, food insecurity |
| Infrastructure & economy | Power, transport, financial instability |

## Setup

```bash
# 1. Clone / copy this project
cd city-risk-scout

# 2. Install dependencies (requires Poetry)
poetry install

# 3. Copy and fill in env file
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the matching API key/URL

# 4. Run
poetry run uvicorn back.main:app --reload
```

Then open `http://localhost:8000` in your browser.

## LLM providers

| Provider | `LLM_PROVIDER` | Required env vars |
|---|---|---|
| Anthropic (Claude) | `anthropic` | `ANTHROPIC_API_KEY` |
| LM Studio / Ollama / vLLM | `openai` | `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| Together AI / OpenRouter | `openai` | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |

## Running tests

```bash
poetry run pytest tests/ -v
```

## Why Scrapling?

- **Adaptive parsing**: survives website layout changes without rewriting selectors
- **Stealth headers**: reduces bot-detection blocks on news sites
- **Concurrent**: all 4 sources scraped in parallel via `ThreadPoolExecutor`
- **Zero extra dependencies**: one library replaces Requests + BeautifulSoup for this use case

## Data sources (all free, no API keys)

| Source | Endpoint | What it provides |
|---|---|---|
| ReliefWeb | `api.reliefweb.int/v1/reports` | UN OCHA humanitarian & crisis reports |
| Reddit | `reddit.com/search.json` | Community discussions |
| Google News | RSS feed | Latest headlines |
| Wikipedia | `en.wikipedia.org/api/rest_v1` | City background |

## Notes

- **Not a replacement for professional risk analysis.** This is a portfolio/demo project.
- Reddit and Google News scraping depends on their public endpoints remaining accessible.
- All scraping uses public, unauthenticated endpoints only.
