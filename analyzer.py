"""
Analyzer module — sends scraped signals to Claude and parses the risk report.

Uses structured JSON output via Claude's API.
"""

import json
import logging
import os

import anthropic

from models import RawSignal, RiskCategory, RiskReport

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SYSTEM_PROMPT = """
You are an expert geopolitical and safety analyst. You receive a list of news signals
scraped from public sources about a specific city, and you produce a structured risk assessment.

Your output must be ONLY a valid JSON object — no markdown fences, no prose before or after.

JSON schema:
{
  "overall_score": <integer 0-100>,
  "overall_level": <"low" | "medium" | "high" | "critical">,
  "executive_summary": <2-3 sentence plain-English summary>,
  "categories": [
    {
      "name": <string, e.g. "Political stability">,
      "level": <"low" | "medium" | "high" | "critical">,
      "score": <integer 0-100>,
      "summary": <1-2 sentences>,
      "signals": [<list of 2-4 short evidence strings from the source data>]
    }
  ],
  "key_sources": [<list of up to 6 source URLs or domain names>],
  "disclaimer": <one-sentence disclaimer about data freshness and limitations>
}

Risk categories to always assess (include all 5):
1. Political stability
2. Civil unrest & crime
3. Natural disaster & environment
4. Health & humanitarian
5. Infrastructure & economy

Score rubric:
  0-25  → low     (no significant indicators)
  26-50 → medium  (some concerning signals, monitor)
  51-75 → high    (clear risk indicators, caution advised)
  76-100→ critical (severe/active risk)

Base your assessment ONLY on the provided signals. If signals are absent or neutral,
default to "low". Never speculate beyond what the evidence supports.
""".strip()


def _build_user_message(city: str, signals: list[RawSignal]) -> str:
    lines = [f"City: {city}\n", f"Total signals collected: {len(signals)}\n", "--- SIGNALS ---"]
    for i, s in enumerate(signals[:60], 1):  # cap at 60 signals to stay within context
        lines.append(
            f"\n[{i}] Source: {s.source}"
            + (f" | Published: {s.published}" if s.published else "")
            + f"\nTitle: {s.title}"
            + (f"\nSnippet: {s.snippet}" if s.snippet else "")
            + (f"\nURL: {s.url}" if s.url else "")
        )
    return "\n".join(lines)


def analyze(city: str, signals: list[RawSignal]) -> RiskReport:
    user_message = _build_user_message(city, signals)

    logger.info("Sending %d signals to Claude for city=%s", len(signals), city)

    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_json = response.content[0].text.strip()

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error("Claude returned invalid JSON: %s\nRaw: %s", exc, raw_json[:500])
        raise ValueError(f"Could not parse Claude's response as JSON: {exc}") from exc

    categories = [
        RiskCategory(
            name=cat["name"],
            level=cat["level"],
            score=cat["score"],
            summary=cat["summary"],
            signals=cat.get("signals", []),
        )
        for cat in data.get("categories", [])
    ]

    return RiskReport(
        city=city,
        overall_score=data["overall_score"],
        overall_level=data["overall_level"],
        executive_summary=data["executive_summary"],
        categories=categories,
        key_sources=data.get("key_sources", []),
        disclaimer=data.get("disclaimer", ""),
        signals_collected=len(signals),
    )
