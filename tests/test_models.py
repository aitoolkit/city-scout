import pytest
from pydantic import ValidationError

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from back.models import CityRequest, RawSignal, RiskCategory, RiskReport


class TestCityRequest:
    def test_valid(self):
        r = CityRequest(city="Kabul")
        assert r.city == "Kabul"

    def test_too_short(self):
        with pytest.raises(ValidationError):
            CityRequest(city="A")

    def test_too_long(self):
        with pytest.raises(ValidationError):
            CityRequest(city="A" * 101)


class TestRawSignal:
    def test_minimal(self):
        s = RawSignal(source="Reddit", title="Some title", snippet="Some text")
        assert s.url is None
        assert s.published is None

    def test_full(self):
        s = RawSignal(
            source="ReliefWeb",
            title="Crisis report",
            snippet="Flooding in the region",
            url="https://reliefweb.int/report/123",
            published="2024-01-15",
        )
        assert s.url == "https://reliefweb.int/report/123"


class TestRiskReport:
    def _make_report(self, **kwargs):
        defaults = dict(
            city="Kyiv",
            overall_score=65,
            overall_level="high",
            executive_summary="Significant conflict risk.",
            categories=[],
            key_sources=["https://reliefweb.int/report/1"],
            disclaimer="For informational purposes only.",
            signals_collected=10,
        )
        defaults.update(kwargs)
        return RiskReport(**defaults)

    def test_valid_report(self):
        r = self._make_report()
        assert r.city == "Kyiv"
        assert r.overall_score == 65

    def test_score_stored_as_int(self):
        r = self._make_report(overall_score=42)
        assert isinstance(r.overall_score, int)

    def test_with_categories(self):
        cat = RiskCategory(
            name="Political stability",
            level="high",
            score=70,
            summary="Ongoing conflict.",
            signals=["Artillery fire reported"],
        )
        r = self._make_report(categories=[cat])
        assert len(r.categories) == 1
        assert r.categories[0].level == "high"
