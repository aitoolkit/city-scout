"""
Config — reads provider settings from environment variables.

LLM_PROVIDER controls which backend is used:
  "anthropic"  → Anthropic API (default, requires ANTHROPIC_API_KEY)
  "openai"     → Any OpenAI-compatible API: LM Studio, Ollama, vLLM, Together, etc.

Quick-start for LM Studio:
  LLM_PROVIDER=openai
  OPENAI_BASE_URL=http://localhost:1234/v1
  OPENAI_MODEL=your-loaded-model-name   # e.g. mistral-7b-instruct
  OPENAI_API_KEY=lm-studio              # LM Studio ignores this but the client requires it
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # Load .env file into environment variables

@dataclass(frozen=True)
class Settings:
    # --- Provider selection ---
    llm_provider: str  # "anthropic" | "openai"

    # --- Anthropic ---
    anthropic_api_key: str
    anthropic_model: str

    # --- OpenAI-compatible (LM Studio, Ollama, vLLM, Together AI…) ---
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_max_tokens: int

    # --- Shared ---
    max_signals: int      # cap signals sent to the LLM per request
    max_prompt_chars: int  # hard char budget for the user message (prevents 413s)


def load() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai").lower(),

        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),

        openai_api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),  # LM Studio ignores this but the client requires it
        openai_base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "llama-3.2-1b-instruct"),
        openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1500")),

        max_signals=int(os.getenv("MAX_SIGNALS", "20")),
        # ~3 500 tokens for user message — safe under a 6 000-TPM limit when
        # the system prompt (~900 tok) and response (~600 tok) are accounted for.
        max_prompt_chars=int(os.getenv("MAX_PROMPT_CHARS", "12000")),
    )


# Singleton — imported once at startup
settings = load()
