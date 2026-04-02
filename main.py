"""
CityRisk Scout — FastAPI backend
"""

import logging
import time
from contextlib import asyncio_contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from analyzer import analyze
from models import CityRequest, RiskReport
from scraper import collect_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CityRisk Scout",
    description="AI-powered city risk assessment using open-source web scraping",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend
frontend_dir = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(frontend_dir / "index.html"))


@app.post("/api/assess", response_model=RiskReport)
async def assess_city(request: CityRequest):
    city = request.city.strip()
    logger.info("Assessment request for city=%s", city)
    start = time.perf_counter()

    # 1. Scrape signals from all sources
    signals = collect_signals(city)
    if not signals:
        raise HTTPException(
            status_code=503,
            detail="Could not collect any signals for this city. Try again or check your network.",
        )

    # 2. Analyze with Claude
    try:
        report = analyze(city, signals)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed = time.perf_counter() - start
    logger.info("Report ready for city=%s in %.1fs | overall=%s (%d)",
                city, elapsed, report.overall_level, report.overall_score)

    return report


@app.get("/health")
async def health():
    return {"status": "ok"}
