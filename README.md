# CityRisk Scout

AI-powered city risk assessment using open-source intelligence.
Scrapes public news and forums with **Scrapling**, then uses **Claude** to generate a structured risk report.

## Architecture

```
User (web form)
  → FastAPI backend
    → Scrapling scraper (concurrent, 4 sources)
      ├── GDELT Project API   (global news event index)
      ├── Reddit JSON API     (public search, no auth)
      ├── Google News RSS     (latest headlines)
      └── Wikipedia REST API  (city background context)
    → Claude API (structured JSON analysis)
  → Risk Report (5 categories, score 0-100, sources)
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

# 2. Create virtualenv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in env file
cp .env.example .env
# Edit .env → add your ANTHROPIC_API_KEY

# 5. Run
uvicorn main:app --reload
```

Open http://localhost:8000 in your browser.

## Why Scrapling?

- **Adaptive parsing**: survives website layout changes without rewriting selectors
- **Stealth headers**: reduces bot-detection blocks on news sites
- **Concurrent**: all 4 sources scraped in parallel via `ThreadPoolExecutor`
- **Zero extra dependencies**: one library replaces Requests + BeautifulSoup for this use case

## Data sources (all free, no API keys)

| Source | Endpoint | What it provides |
|---|---|---|
| GDELT | `api.gdeltproject.org/api/v2/doc` | 250+ language news index |
| Reddit | `reddit.com/search.json` | Community discussions |
| Google News | RSS feed | Latest headlines |
| Wikipedia | `en.wikipedia.org/api/rest_v1` | City background |

## Notes

- **Not a replacement for professional risk analysis.** This is a portfolio/demo project.
- Reddit and Google News scraping depends on their public endpoints remaining accessible.
- GDELT covers news events from 1979 onwards with near-real-time updates.
- All scraping respects public, unauthenticated endpoints only.
