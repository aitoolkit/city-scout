"""
Analyzer — LLM provider abstraction.

Supports:
  - Anthropic API  (LLM_PROVIDER=anthropic)
  - Any OpenAI-compatible API  (LLM_PROVIDER=openai)
    Tested with: LM Studio, Ollama, vLLM, Together AI, OpenRouter

The system prompt enforces strict JSON output so both providers return
the same structure. Local models vary in instruction-following quality —
see the JSON repair fallback inside _extract_json().
"""

import json
import logging
import re
from abc import ABC, abstractmethod

from .models import RawSignal, RiskCategory, RiskReport
from .config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are an expert geopolitical and safety analyst. You receive a list of news signals
scraped from public sources about a specific city, and you produce a structured risk assessment.

Your output must be ONLY a valid JSON object.
Do NOT include markdown code fences (```), do NOT add any text before or after the JSON.
Start your response with { and end it with }.

JSON schema:
{
  "overall_score": <integer 0-100>,
  "overall_level": <"low" | "medium" | "high" | "critical">,
  "executive_summary": "<2-3 sentence plain-English summary>",
  "categories": [
    {
      "name": "<category name>",
      "level": "<low | medium | high | critical>",
      "score": <integer 0-100>,
      "summary": "<1-2 sentences>",
      "signals": ["<evidence string 1>", "<evidence string 2>"]
    }
  ],
  "key_sources": ["<url or domain>"],
  "disclaimer": "<one-sentence disclaimer>"
}

Risk categories — always include all 5 in this order:
1. Political stability
2. Civil unrest & crime
3. Natural disaster & environment
4. Health & humanitarian
5. Infrastructure & economy

Score rubric:
  0-25  → low      (no significant indicators)
  26-50 → medium   (some concerning signals, monitor)
  51-75 → high     (clear risk indicators, caution advised)
  76-100→ critical (severe/active risk)

Base your assessment ONLY on the provided signals.
If signals are absent or neutral, default to "low".
Never speculate beyond what the evidence supports.
key_sources must be full absolute URLs (starting with http:// or https://). Never include localhost or relative paths.
""".strip()


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Common interface for all LLM backends."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the raw text completion for a system + user message pair."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in logs and the /health endpoint."""


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        import anthropic
        if not settings.anthropic_api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env or switch to LLM_PROVIDER=openai."
            )
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    @property
    def display_name(self) -> str:
        return f"Anthropic / {self._model}"

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# OpenAI-compatible provider  (LM Studio, Ollama, vLLM, Together, OpenRouter…)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self) -> None:
        from openai import OpenAI
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._model = settings.openai_model
        self._max_tokens = settings.openai_max_tokens

    @property
    def display_name(self) -> str:
        return f"OpenAI-compatible / {self._model} @ {settings.openai_base_url}"

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,  # low temp → more deterministic JSON
        )
        return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def _build_provider() -> LLMProvider:
    if settings.llm_provider == "openai":
        provider = OpenAICompatibleProvider()
    else:
        provider = AnthropicProvider()
    logger.info("LLM provider: %s", provider.display_name)
    return provider


_provider: LLMProvider = _build_provider()


def get_provider() -> LLMProvider:
    """Expose the active provider (used by the /health endpoint)."""
    return _provider


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> str:
    """
    Strip markdown fences and any prose around the JSON object.
    Local models often wrap output in ```json ... ``` despite instructions.
    """
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = raw.replace("```", "").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def _sanitize_sources(sources: list[str]) -> list[str]:
    """Keep only absolute http/https URLs, drop localhost and relative paths."""
    cleaned = []
    for s in sources:
        s = s.strip()
        if s.startswith("http://") or s.startswith("https://"):
            if "localhost" not in s and "127.0.0.1" not in s:
                cleaned.append(s)
    return cleaned


def _parse_response(raw: str, city: str, signals: list[RawSignal]) -> RiskReport:
    cleaned = _extract_json(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON.\nRaw:\n%s", raw)
        raise ValueError(
            f"Could not parse the model's response as JSON: {exc}\n"
            "Try a more capable model or reduce MAX_SIGNALS in .env."
        ) from exc

    categories = [
        RiskCategory(
            name=cat["name"],
            level=cat.get("level", "low"),
            score=int(cat.get("score", 0)),
            summary=cat.get("summary", ""),
            signals=cat.get("signals", []),
        )
        for cat in data.get("categories", [])
    ]

    return RiskReport(
        city=city,
        overall_score=int(data.get("overall_score", 0)),
        overall_level=data.get("overall_level", "low"),
        executive_summary=data.get("executive_summary", ""),
        categories=categories,
        key_sources=_sanitize_sources(data.get("key_sources", [])),
        disclaimer=data.get("disclaimer", ""),
        signals_collected=len(signals),
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def _build_user_message(city: str, signals: list[RawSignal]) -> str:
    cap = settings.max_signals
    lines = [
        f"City: {city}",
        f"Total signals collected: {len(signals)} (sending top {min(len(signals), cap)})",
        "",
        "--- SIGNALS ---",
    ]
    for i, s in enumerate(signals[:cap], 1):
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
    logger.info(
        "Analyzing city=%s | signals=%d | provider=%s",
        city, len(signals), _provider.display_name,
    )
    raw = _provider.complete(system=SYSTEM_PROMPT, user=user_message)
    return _parse_response(raw, city, signals)
