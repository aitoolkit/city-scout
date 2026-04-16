import json
import pytest
from unittest.mock import patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestScrapeReliefweb:
    def test_returns_signals_on_valid_response(self):
        from back.scraper import _scrape_reliefweb
        payload = {
            "data": [
                {
                    "fields": {
                        "title": "Flood emergency in Dhaka",
                        "url": "https://reliefweb.int/report/123",
                        "date": {"created": "2024-06-01"},
                        "source": [{"name": "OCHA"}],
                    }
                }
            ]
        }
        with patch("back.scraper._safe_get", return_value=json.dumps(payload)):
            signals = _scrape_reliefweb("Dhaka")
        assert len(signals) == 1
        assert signals[0].title == "Flood emergency in Dhaka"
        assert signals[0].source == "ReliefWeb / OCHA"
        assert signals[0].url == "https://reliefweb.int/report/123"

    def test_returns_empty_on_fetch_failure(self):
        from back.scraper import _scrape_reliefweb
        with patch("back.scraper._safe_get", return_value=None):
            signals = _scrape_reliefweb("Dhaka")
        assert signals == []

    def test_returns_empty_on_invalid_json(self):
        from back.scraper import _scrape_reliefweb
        with patch("back.scraper._safe_get", return_value="not json"):
            signals = _scrape_reliefweb("Dhaka")
        assert signals == []

    def test_uses_reliefweb_fallback_when_no_source(self):
        from back.scraper import _scrape_reliefweb
        payload = {
            "data": [
                {
                    "fields": {
                        "title": "Crisis report",
                        "url": "https://reliefweb.int/report/456",
                        "date": {"created": "2024-06-01"},
                        "source": [],
                    }
                }
            ]
        }
        with patch("back.scraper._safe_get", return_value=json.dumps(payload)):
            signals = _scrape_reliefweb("Lagos")
        assert signals[0].source == "ReliefWeb / ReliefWeb"


class TestScrapeReddit:
    def test_returns_signals_on_valid_response(self):
        from back.scraper import _scrape_reddit
        payload = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Is Nairobi safe?",
                            "selftext": "Planning a trip…",
                            "permalink": "/r/travel/comments/abc",
                            "created_utc": 1700000000,
                        }
                    }
                ]
            }
        }
        with patch("back.scraper._safe_get", return_value=json.dumps(payload)):
            signals = _scrape_reddit("Nairobi")
        assert len(signals) == 1
        assert signals[0].source == "Reddit"
        assert "reddit.com" in signals[0].url

    def test_returns_empty_on_fetch_failure(self):
        from back.scraper import _scrape_reddit
        with patch("back.scraper._safe_get", return_value=None):
            assert _scrape_reddit("Nairobi") == []


class TestScrapeWikipedia:
    def test_returns_signal_on_valid_response(self):
        from back.scraper import _scrape_wikipedia
        payload = {
            "title": "Kabul",
            "extract": "Kabul is the capital of Afghanistan.",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Kabul"}},
        }
        with patch("back.scraper._safe_get", return_value=json.dumps(payload)):
            signals = _scrape_wikipedia("Kabul")
        assert len(signals) == 1
        assert signals[0].title == "Kabul"
        assert signals[0].url == "https://en.wikipedia.org/wiki/Kabul"

    def test_returns_empty_when_no_extract(self):
        from back.scraper import _scrape_wikipedia
        payload = {"title": "Unknown", "extract": ""}
        with patch("back.scraper._safe_get", return_value=json.dumps(payload)):
            assert _scrape_wikipedia("Unknown") == []

    def test_returns_empty_on_fetch_failure(self):
        from back.scraper import _scrape_wikipedia
        with patch("back.scraper._safe_get", return_value=None):
            assert _scrape_wikipedia("Kabul") == []


class TestCollectSignals:
    def test_aggregates_all_sources(self):
        from back.scraper import collect_signals
        from back.models import RawSignal

        dummy = [RawSignal(source="Test", title="T", snippet="S")]

        with patch("back.scraper._scrape_reliefweb", return_value=dummy), \
             patch("back.scraper._scrape_reddit", return_value=dummy), \
             patch("back.scraper._scrape_google_news", return_value=dummy), \
             patch("back.scraper._scrape_wikipedia", return_value=dummy):
            signals = collect_signals("Testville")

        assert len(signals) == 4

    def test_tolerates_source_failure(self):
        from back.scraper import collect_signals
        from back.models import RawSignal

        dummy = [RawSignal(source="Test", title="T", snippet="S")]

        with patch("back.scraper._scrape_reliefweb", side_effect=Exception("network error")), \
             patch("back.scraper._scrape_reddit", return_value=dummy), \
             patch("back.scraper._scrape_google_news", return_value=[]), \
             patch("back.scraper._scrape_wikipedia", return_value=[]):
            signals = collect_signals("Testville")

        assert len(signals) == 1
