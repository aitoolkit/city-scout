# CityRisk Scout

**AI-powered risk assessment for any city in the world — from open-source intelligence.**

Type a city name. The tool scrapes four public data sources in parallel, feeds the results to an LLM, and returns a structured risk report in seconds. No proprietary data feeds, no paid intelligence subscriptions.

> **Disclaimer:** This is a portfolio/research tool. Risk scores depend on what public sources happen to publish on a given day and should not be used as a substitute for professional security analysis.

---

## Demo

<!-- Add a screenshot or GIF of an actual report here (e.g. Kyiv or Caracas) -->
<!-- Tip: run the app, assess a high-signal city, and screenshot the result -->
> _Screenshot coming soon_

---

## How it works

```
User types a city
  → FastAPI backend
    → Scrapling scraper (4 sources, concurrent)
        ├── ReliefWeb API   — UN OCHA humanitarian & crisis reports
        ├── Reddit JSON API — public community discussions (no auth)
        ├── Google News RSS — latest headlines
        └── Wikipedia REST  — city background context
    → Signal list trimmed to token budget (no 413 errors)
    → LLM prompt → structured JSON response
  → Risk report: 5 categories, score 0-100, key sources
```

---

## Risk categories

| # | Category | What it covers |
|---|---|---|
| 1 | Political stability | Elections, coups, sanctions, governance crises |
| 2 | Civil unrest & crime | Protests, violence, crime indicators |
| 3 | Natural disaster & environment | Earthquakes, floods, wildfires, pollution |
| 4 | Health & humanitarian | Epidemics, displacement, food insecurity |
| 5 | Infrastructure & economy | Power outages, transport, financial instability |

Each category gets a score (0–100) and a level: **low / medium / high / critical**.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/city-risk-scout.git
cd city-risk-scout

# 2. Install (requires Python 3.13+ and Poetry)
poetry install

# 3. Configure
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the matching API key or local URL

# 4. Run
poetry run uvicorn back.main:app --reload
```

Open `http://localhost:8000` in your browser.

---

## LLM providers

The analyzer is provider-agnostic — swap backends via a single env var.

| Provider | `LLM_PROVIDER` | Required vars |
|---|---|---|
| **Anthropic** (Claude) | `anthropic` | `ANTHROPIC_API_KEY` |
| **LM Studio / Ollama** (local, free) | `openai` | `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| **Groq** (fast free tier) | `openai` | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| **Together AI / OpenRouter** | `openai` | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |

Any OpenAI-compatible API works. The abstraction lives in [`back/analyzer.py`](back/analyzer.py).

### Token budget for free-tier APIs

Free-tier models (e.g. Groq's 6 000-TPM limit) can hit 413 errors with large signal sets.
Two env vars control the payload size — see `.env.example` for guidance:

```env
MAX_SIGNALS=20        # signals passed to the LLM (default: 20)
MAX_PROMPT_CHARS=12000 # hard char budget before signals are cut (default: 12000)
```

---

## Project structure

```
city-risk-scout/
├── back/
│   ├── main.py       # FastAPI app, /api/assess endpoint
│   ├── scraper.py    # Scrapling-based concurrent scraper (4 sources)
│   ├── analyzer.py   # LLM provider abstraction + prompt builder
│   ├── models.py     # Pydantic models (RawSignal, RiskReport, …)
│   └── config.py     # Settings singleton (reads .env)
├── front/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── tests/
├── .env.example
└── pyproject.toml
```

---

## Data sources

All free, no API keys required for scraping.

| Source | Endpoint | Signal type |
|---|---|---|
| ReliefWeb (UN OCHA) | `api.reliefweb.int/v1/reports` | Humanitarian & crisis reports |
| Reddit | `reddit.com/search.json` | Community discussions |
| Google News | RSS feed | Latest headlines |
| Wikipedia | `en.wikipedia.org/api/rest_v1` | City background |

---

## Running tests

```bash
poetry run pytest tests/ -v
```

---

## Why Scrapling?

- Adaptive parsing — survives layout changes without rewriting selectors
- Stealth headers — reduces bot-detection blocks on news sites
- Concurrent — all 4 sources scraped in parallel via `ThreadPoolExecutor`
- Replaces Requests + BeautifulSoup for this use case with a single dependency
