from pydantic import BaseModel, Field
from typing import Optional


class CityRequest(BaseModel):
    city: str = Field(..., min_length=2, max_length=100, description="City name to assess")


class RawSignal(BaseModel):
    source: str
    title: str
    snippet: str
    url: Optional[str] = None
    published: Optional[str] = None


class RiskCategory(BaseModel):
    name: str
    level: str  # low | medium | high | critical
    score: int  # 0-100
    summary: str
    signals: list[str]


class RiskReport(BaseModel):
    city: str
    overall_score: int  # 0-100
    overall_level: str  # low | medium | high | critical
    executive_summary: str
    categories: list[RiskCategory]
    key_sources: list[str]
    disclaimer: str
    signals_collected: int
