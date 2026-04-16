import json
import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from back.models import RawSignal


SAMPLE_SIGNALS = [
    RawSignal(source="ReliefWeb", title="Flood warning", snippet="Heavy rain expected", url="https://reliefweb.int/1"),
    RawSignal(source="Reddit", title="Safety tips", snippet="Stay indoors", url="https://reddit.com/r/1"),
]

VALID_LLM_RESPONSE = json.dumps({
    "overall_score": 55,
    "overall_level": "high",
    "executive_summary": "The city faces elevated natural disaster risk.",
    "categories": [
        {
            "name": "Political stability",
            "level": "low",
            "score": 10,
            "summary": "No significant political unrest.",
            "signals": [],
        },
        {
            "name": "Civil unrest & crime",
            "level": "low",
            "score": 15,
            "summary": "Crime levels appear normal.",
            "signals": [],
        },
        {
            "name": "Natural disaster & environment",
            "level": "high",
            "score": 70,
            "summary": "Flooding risk elevated.",
            "signals": ["Flood warning issued"],
        },
        {
            "name": "Health & humanitarian",
            "level": "medium",
            "score": 40,
            "summary": "Moderate humanitarian concern.",
            "signals": [],
        },
        {
            "name": "Infrastructure & economy",
            "level": "low",
            "score": 20,
            "summary": "Infrastructure stable.",
            "signals": [],
        },
    ],
    "key_sources": ["https://reliefweb.int/1", "https://reddit.com/r/1"],
    "disclaimer": "This report is for informational purposes only.",
})


class TestExtractJson:
    def test_clean_json(self):
        from back.analyzer import _extract_json
        raw = '{"key": "value"}'
        assert _extract_json(raw) == '{"key": "value"}'

    def test_strips_markdown_fences(self):
        from back.analyzer import _extract_json
        raw = '```json\n{"key": "value"}\n```'
        result = _extract_json(raw)
        assert result == '{"key": "value"}'

    def test_strips_leading_prose(self):
        from back.analyzer import _extract_json
        raw = 'Here is the JSON:\n{"key": "value"}\nDone.'
        result = _extract_json(raw)
        assert result == '{"key": "value"}'


class TestSanitizeSources:
    def test_keeps_valid_https(self):
        from back.analyzer import _sanitize_sources
        assert _sanitize_sources(["https://reliefweb.int/report"]) == ["https://reliefweb.int/report"]

    def test_keeps_valid_http(self):
        from back.analyzer import _sanitize_sources
        assert _sanitize_sources(["http://example.com"]) == ["http://example.com"]

    def test_drops_localhost(self):
        from back.analyzer import _sanitize_sources
        assert _sanitize_sources(["http://localhost:8000/api"]) == []

    def test_drops_127(self):
        from back.analyzer import _sanitize_sources
        assert _sanitize_sources(["http://127.0.0.1/report"]) == []

    def test_drops_relative_paths(self):
        from back.analyzer import _sanitize_sources
        assert _sanitize_sources(["/api/assess", "reports/flood"]) == []

    def test_mixed(self):
        from back.analyzer import _sanitize_sources
        sources = [
            "https://reliefweb.int/1",
            "http://localhost:8000/api",
            "/relative/path",
            "https://reddit.com/r/news",
        ]
        result = _sanitize_sources(sources)
        assert result == ["https://reliefweb.int/1", "https://reddit.com/r/news"]

    def test_strips_whitespace(self):
        from back.analyzer import _sanitize_sources
        assert _sanitize_sources(["  https://reliefweb.int/1  "]) == ["https://reliefweb.int/1"]


class TestParseResponse:
    def test_valid_response(self):
        from back.analyzer import _parse_response
        report = _parse_response(VALID_LLM_RESPONSE, "TestCity", SAMPLE_SIGNALS)
        assert report.city == "TestCity"
        assert report.overall_score == 55
        assert report.overall_level == "high"
        assert len(report.categories) == 5
        assert report.signals_collected == 2

    def test_invalid_json_raises(self):
        from back.analyzer import _parse_response
        with pytest.raises(ValueError, match="Could not parse"):
            _parse_response("not json at all", "TestCity", SAMPLE_SIGNALS)

    def test_markdown_wrapped_json(self):
        from back.analyzer import _parse_response
        wrapped = f"```json\n{VALID_LLM_RESPONSE}\n```"
        report = _parse_response(wrapped, "TestCity", SAMPLE_SIGNALS)
        assert report.overall_score == 55

    def test_localhost_sources_filtered(self):
        from back.analyzer import _parse_response
        response_with_localhost = json.loads(VALID_LLM_RESPONSE)
        response_with_localhost["key_sources"].append("http://localhost:8000/")
        report = _parse_response(json.dumps(response_with_localhost), "TestCity", SAMPLE_SIGNALS)
        assert not any("localhost" in s for s in report.key_sources)
