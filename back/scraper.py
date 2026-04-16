"""
Scraper module — uses Scrapling to collect signals from multiple free sources.

Sources:
  - ReliefWeb API      : UN OCHA humanitarian/disaster/crisis reports, no key needed
  - Reddit JSON API    : public search endpoint, no auth needed
  - Google News RSS    : XML feed for latest headlines
  - Wikipedia REST API : city context and background
"""

import json
import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

from scrapling.fetchers import Fetcher

from .models import RawSignal

logger = logging.getLogger(__name__)

_fetcher = Fetcher()


def _safe_get(url: str, timeout: int = 10) -> str | None:
    """Fetch a URL via Scrapling, returning raw text or None on failure."""
    try:
        page = _fetcher.get(url, timeout=timeout, stealthy_headers=True)
        return page.body
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# ReliefWeb (UN OCHA) — humanitarian / disaster / crisis reports (JSON, free, no key)
# ---------------------------------------------------------------------------

def _scrape_reliefweb(city: str, max_articles: int = 15) -> list[RawSignal]:
    signals: list[RawSignal] = []
    query = quote_plus(f"{city} disaster OR crisis OR conflict OR risk OR safety")
    url = (
        f"https://api.reliefweb.int/v1/reports"
        f"?appname=city-risk-scout"
        f"&query[value]={query}"
        f"&fields[include][]=title"
        f"&fields[include][]=url"
        f"&fields[include][]=date.created"
        f"&fields[include][]=source"
        f"&limit={max_articles}"
        f"&sort[]=date.created:desc"
    )
    raw = _safe_get(url, timeout=15)
    if not raw:
        return signals

    try:
        data = json.loads(raw)
        for item in data.get("data", []):
            fields = item.get("fields", {})
            title = fields.get("title", "")
            art_url = fields.get("url", "")
            published = fields.get("date", {}).get("created", "")
            sources = fields.get("source", [])
            source_name = sources[0].get("name", "ReliefWeb") if sources else "ReliefWeb"
            signals.append(RawSignal(
                source=f"ReliefWeb / {source_name}",
                title=title,
                snippet=published,
                url=art_url,
                published=published,
            ))
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("ReliefWeb parse error: %s", exc)

    return signals


# ---------------------------------------------------------------------------
# Reddit — public JSON search (no auth, old API endpoint)
# ---------------------------------------------------------------------------

def _scrape_reddit(city: str, max_posts: int = 20) -> list[RawSignal]:
    signals: list[RawSignal] = []
    # Use Reddit's public .json endpoint — works without credentials
    query = quote_plus(f"{city} safety risk crime disaster")
    url = f"https://www.reddit.com/search.json?q={query}&sort=new&limit={max_posts}&t=month"

    raw = _safe_get(url)
    if not raw:
        return signals

    try:
        data = json.loads(raw)
        posts = data.get("data", {}).get("children", [])
        for post in posts:
            p = post.get("data", {})
            title = p.get("title", "")
            selftext = p.get("selftext", "")[:300]
            snippet = selftext if selftext else p.get("url", "")
            signals.append(RawSignal(
                source="Reddit",
                title=title,
                snippet=snippet,
                url=f"https://reddit.com{p.get('permalink', '')}",
                published=str(p.get("created_utc", "")),
            ))
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Reddit parse error: %s", exc)

    return signals


# ---------------------------------------------------------------------------
# Google News RSS — latest headlines (XML feed, no key)
# ---------------------------------------------------------------------------

def _scrape_google_news(city: str, max_items: int = 15) -> list[RawSignal]:
    signals: list[RawSignal] = []
    query = quote_plus(f"{city} danger OR safety OR violence OR disaster OR unrest")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    raw = _safe_get(url)
    if not raw:
        return signals

    try:
        # Strip potential encoding declarations that confuse ET
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            return signals
        for i, item in enumerate(channel.findall("item")):
            if i >= max_items:
                break
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub = item.findtext("pubDate", "")
            desc_el = item.find("description")
            snippet = desc_el.text[:300] if desc_el is not None and desc_el.text else ""
            signals.append(RawSignal(
                source="Google News",
                title=title,
                snippet=snippet,
                url=link,
                published=pub,
            ))
    except ET.ParseError as exc:
        logger.warning("Google News XML parse error: %s", exc)

    return signals


# ---------------------------------------------------------------------------
# Wikipedia — city context (REST API)
# ---------------------------------------------------------------------------

def _scrape_wikipedia(city: str) -> list[RawSignal]:
    city_slug = city.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(city_slug)}"

    raw = _safe_get(url)
    if not raw:
        return []

    try:
        data = json.loads(raw)
        extract = data.get("extract", "")
        if extract:
            return [RawSignal(
                source="Wikipedia",
                title=data.get("title", city),
                snippet=extract[:500],
                url=data.get("content_urls", {}).get("desktop", {}).get("page"),
            )]
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Wikipedia parse error: %s", exc)

    return []


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def collect_signals(city: str) -> list[RawSignal]:
    """
    Gather signals from all sources concurrently using threads
    (Scrapling's Fetcher is synchronous, so we use ThreadPoolExecutor).
    """
    import concurrent.futures

    tasks = [
        lambda c=city: _scrape_reliefweb(c),
        lambda c=city: _scrape_reddit(c),
        lambda c=city: _scrape_google_news(c),
        lambda c=city: _scrape_wikipedia(c),
    ]

    all_signals: list[RawSignal] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            try:
                all_signals.extend(future.result())
            except Exception as exc:
                logger.warning("Scraping task failed: %s", exc)

    logger.info("Collected %d signals for city=%s", len(all_signals), city)
    return all_signals
