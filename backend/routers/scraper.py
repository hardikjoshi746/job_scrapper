"""
Job Scraper router — /api/scraper

Endpoints:
  POST /search   — run a multi-source job scrape (rate-limited 10/hour per user)
  POST /save     — convert a scraped job into a tracked Application
  GET  /history  — return the user's 24-hour scrape cache
"""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_db
from models import Application, ScrapedJob, User
from schemas import (
    SaveScrapedJobRequest,
    ScrapedJobOut,
    ScrapeRequest,
    ScrapeResponse,
)
from services.job_scraper import scrape_jobs
from services.security import get_user_key, sanitize_text

router = APIRouter()
limiter = Limiter(key_func=get_user_key)


# ---------------------------------------------------------------------------
# POST /api/scraper/search
# ---------------------------------------------------------------------------

@router.post("/search", response_model=ScrapeResponse)
@limiter.limit("10/hour")
async def search_scraped_jobs(
    request: Request,
    body: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregate job listings from multiple sources.
    Rate-limited to 10 requests per hour per user.
    """
    try:
        keyword = sanitize_text(body.keyword, max_len=100)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        location = sanitize_text(body.location or "remote", max_len=100)
    except ValueError:
        location = "remote"

    # Validate requested sources
    valid_sources = {"google_jobs", "linkedin", "adzuna", "remoteok", "arbeitnow", "weworkremotely", "indeed_rss"}
    if body.sources:
        bad = [s for s in body.sources if s not in valid_sources]
        if bad:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown source(s): {bad}. Valid: {sorted(valid_sources)}",
            )

    # Validate filter values
    valid_levels = {"entry", "associate", "mid", "senior", "lead"}
    valid_dates = {"any", "day", "week", "month"}
    if body.experience_level and body.experience_level not in valid_levels:
        raise HTTPException(status_code=422, detail=f"Invalid experience_level. Valid: {sorted(valid_levels)}")
    if body.date_posted and body.date_posted not in valid_dates:
        raise HTTPException(status_code=422, detail=f"Invalid date_posted. Valid: {sorted(valid_dates)}")

    raw_results, counts, errors = await scrape_jobs(
        keyword=keyword,
        location=location,
        sources=body.sources,
        user_id=current_user.id,
        db=db,
        experience_level=body.experience_level,
        date_posted=body.date_posted,
    )

    # Re-query DB to get real IDs for all upserted rows
    job_urls = [r["job_url"] for r in raw_results]
    db_rows = (
        db.query(ScrapedJob)
        .filter(
            ScrapedJob.user_id == current_user.id,
            ScrapedJob.job_url.in_(job_urls),
        )
        .all()
    )
    url_to_row: dict[str, ScrapedJob] = {row.job_url: row for row in db_rows}

    out: list[ScrapedJobOut] = []
    for r in raw_results:
        row = url_to_row.get(r["job_url"])
        if row is None:
            continue
        tags: list[str] = []
        if row.tags:
            try:
                tags = json.loads(row.tags)
            except Exception:
                tags = []
        out.append(
            ScrapedJobOut(
                id=row.id,
                source=row.source,
                job_url=row.job_url,
                title=row.title,
                company=row.company,
                location=row.location,
                description=row.description,
                salary_min=row.salary_min,
                salary_max=row.salary_max,
                currency=row.currency,
                tags=tags,
                posted_at=row.posted_at,
                is_remote=bool(row.is_remote),
            )
        )

    return ScrapeResponse(
        total=len(out),
        sources=counts,
        results=out,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# POST /api/scraper/save
# ---------------------------------------------------------------------------

@router.post("/save")
async def save_scraped_job(
    body: SaveScrapedJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert a scraped job into a tracked Application."""
    existing = (
        db.query(Application)
        .filter(
            Application.job_url == body.job_url,
            Application.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Job is already in your tracker")

    app = Application(
        user_id=current_user.id,
        job_title=body.title,
        company=body.company or "Unknown",
        location=body.location,
        job_url=body.job_url,
        job_description=body.job_description,
        status="saved",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"message": "Saved", "application_id": app.id}


# ---------------------------------------------------------------------------
# GET /api/scraper/history
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[ScrapedJobOut])
async def get_scrape_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return jobs fetched in the last 24 hours for this user."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    rows = (
        db.query(ScrapedJob)
        .filter(
            ScrapedJob.user_id == current_user.id,
            ScrapedJob.fetched_at >= cutoff,
        )
        .order_by(ScrapedJob.fetched_at.desc())
        .limit(200)
        .all()
    )

    result: list[ScrapedJobOut] = []
    for row in rows:
        tags: list[str] = []
        if row.tags:
            try:
                tags = json.loads(row.tags)
            except Exception:
                pass
        result.append(
            ScrapedJobOut(
                id=row.id,
                source=row.source,
                job_url=row.job_url,
                title=row.title,
                company=row.company,
                location=row.location,
                description=row.description,
                salary_min=row.salary_min,
                salary_max=row.salary_max,
                currency=row.currency,
                tags=tags,
                posted_at=row.posted_at,
                is_remote=bool(row.is_remote),
            )
        )
    return result