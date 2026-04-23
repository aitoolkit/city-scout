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

### Step 1 — Request intake ([`back/main.py`](back/main.py))

The frontend sends a `POST /api/assess` request with a city name. FastAPI validates it (2–100 chars) via a Pydantic model and passes it to the pipeline.

### Step 2 — Concurrent scraping ([`back/scraper.py`](back/scraper.py))

Four scrapers run in parallel via `ThreadPoolExecutor`. Each targets a different type of public source:

| Source | Query strategy | What it returns |
|---|---|---|
| **ReliefWeb** (UN OCHA) | `{city} disaster OR crisis OR conflict OR risk` | Humanitarian & crisis reports with date and publisher |
| **Reddit** | `{city} safety risk crime disaster` — sorted by `new`, last month | Post titles + text snippets |
| **Google News** | `{city} danger OR safety OR violence OR disaster OR unrest` | RSS headlines with publication date |
| **Wikipedia** | Direct page summary for the city slug | Background context (population, geography, political status) |

All endpoints are free and require no authentication. Scrapling handles stealth headers to reduce bot-detection blocks.

### Step 3 — Token budget enforcement ([`back/analyzer.py`](back/analyzer.py) → `_build_user_message`)

Raw signals are assembled into a prompt one by one. Two guards prevent hitting API token limits:

1. **`MAX_SIGNALS`** (default: 20) — hard cap on the number of signals considered.
2. **`MAX_PROMPT_CHARS`** (default: 12 000 chars ≈ 3 000 tokens) — the loop stops adding signals the moment the running character count would exceed the budget. Each snippet is also pre-truncated to 150 chars.

This makes the tool safe to use on free-tier APIs (e.g. Groq's 6 000-TPM limit) without manual tuning.

### Step 4 — LLM analysis ([`back/analyzer.py`](back/analyzer.py) → `analyze`)

The trimmed signal list is sent to the configured LLM provider with a structured system prompt that enforces a specific JSON schema. The prompt instructs the model to:
- score each of the 5 risk categories from 0 to 100
- map scores to severity levels (low / medium / high / critical)
- cite only evidence present in the signals (no speculation)
- return only a JSON object — no markdown fences, no prose

The provider abstraction (`LLMProvider` ABC) means the same prompt works identically whether the backend is Anthropic, a local Ollama model, or any OpenAI-compatible API.

### Step 5 — Response parsing and validation ([`back/analyzer.py`](back/analyzer.py) → `_parse_response`)

The raw LLM output goes through two cleanup passes:
- **`_extract_json`** — strips markdown fences and prose that some models add despite instructions, then extracts the outermost `{ … }` block.
- **`_sanitize_sources`** — drops any `key_sources` entries that are not absolute `http(s)://` URLs (guards against hallucinated or relative paths).

The cleaned JSON is validated into a `RiskReport` Pydantic model and returned as the API response.

### Step 6 — Rendering ([`front/app.js`](front/app.js))

The frontend receives the `RiskReport` JSON and renders the five category cards, the overall score badge, the executive summary, and the clickable source URLs — all without a page reload.

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
