"""
Multi-source job aggregation service.

Fetches job listings from multiple free/public sources in parallel:
  - Adzuna (existing API, key-based)
  - RemoteOK (public API, no key)
  - Arbeitnow (public API, no key)
  - We Work Remotely (public Atom feed)
  - Indeed (public RSS feed)

Security guardrails applied per request:
  - Per-source 15s timeout (httpx)
  - 2 MB response size cap (bounded_get)
  - Honest User-Agent header
  - Error isolation: one failed source never kills others
  - In-memory + DB deduplication by job_url
"""

import asyncio
import json
import re
import urllib.parse
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from config import settings
from services.security import APP_USER_AGENT, REQUEST_TIMEOUT, bounded_get


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------

def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": APP_USER_AGENT},
        follow_redirects=True,
    )


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


# ---------------------------------------------------------------------------
# Per-source fetchers — each returns list[dict] or raises
# ---------------------------------------------------------------------------

async def _fetch_adzuna(keyword: str, location: str, client: httpx.AsyncClient, date_posted: Optional[str] = None) -> list[dict]:
    if not getattr(settings, "adzuna_app_id", None) or not getattr(settings, "adzuna_app_key", None):
        raise RuntimeError("Adzuna API credentials not configured")

    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "what": keyword,
        "where": location,
        "results_per_page": 20,
        "sort_by": "date" if date_posted and date_posted != "any" else "relevance",
    }
    # Adzuna max_days_old param
    _days_map = {"day": 1, "week": 7, "month": 30}
    if date_posted in _days_map:
        params["max_days_old"] = _days_map[date_posted]
    data = await bounded_get(client, url, params=params)
    payload = json.loads(data)

    results = []
    for j in payload.get("results", []):
        job_location = (j.get("location") or {}).get("display_name", "")
        results.append({
            "source": "adzuna",
            "job_url": j.get("redirect_url", ""),
            "title": j.get("title", ""),
            "company": (j.get("company") or {}).get("display_name"),
            "location": job_location,
            "description": _strip_html(j.get("description", "")),
            "salary_min": j.get("salary_min"),
            "salary_max": j.get("salary_max"),
            "currency": "USD",
            "tags": [],
            "posted_at": _parse_dt(j.get("created")),
            "is_remote": "remote" in job_location.lower(),
        })
    return results


async def _fetch_remoteok(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    data = await bounded_get(client, "https://remoteok.com/api")
    jobs = json.loads(data)
    # First element is a legal notice object — skip it
    keyword_lower = keyword.lower()
    results = []
    for j in jobs[1:]:
        if not isinstance(j, dict):
            continue
        title = j.get("position", "")
        tag_str = " ".join(j.get("tags") or []).lower()
        if keyword_lower not in title.lower() and keyword_lower not in tag_str:
            continue
        epoch = j.get("epoch")
        results.append({
            "source": "remoteok",
            "job_url": j.get("url", ""),
            "title": title,
            "company": j.get("company"),
            "location": "Remote",
            "description": _strip_html(j.get("description", "")),
            "salary_min": j.get("salary_min"),
            "salary_max": j.get("salary_max"),
            "currency": "USD",
            "tags": j.get("tags") or [],
            "posted_at": datetime.utcfromtimestamp(int(epoch)) if epoch else None,
            "is_remote": True,
        })
        if len(results) >= 20:
            break
    return results


async def _fetch_arbeitnow(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    params = {"search": keyword}
    data = await bounded_get(
        client,
        "https://www.arbeitnow.com/api/job-board-api",
        params=params,
    )
    payload = json.loads(data)
    results = []
    for j in payload.get("data", [])[:20]:
        created_at = j.get("created_at")
        results.append({
            "source": "arbeitnow",
            "job_url": j.get("url", ""),
            "title": j.get("title", ""),
            "company": j.get("company_name"),
            "location": j.get("location"),
            "description": _strip_html(j.get("description", "")),
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "tags": j.get("tags") or [],
            "posted_at": datetime.utcfromtimestamp(int(created_at)) if created_at else None,
            "is_remote": bool(j.get("remote", False)),
        })
    return results


async def _fetch_wwr_rss(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    encoded = urllib.parse.quote(keyword)
    url = f"https://weworkremotely.com/remote-jobs/search.atom?term={encoded}"
    data = await bounded_get(client, url)
    feed = feedparser.parse(data.decode("utf-8", errors="replace"))
    results = []
    for entry in feed.entries[:20]:
        published = _parse_feedparser_time(entry.get("published_parsed"))
        results.append({
            "source": "weworkremotely",
            "job_url": entry.get("link", ""),
            "title": entry.get("title", ""),
            "company": entry.get("author"),
            "location": "Remote",
            "description": _strip_html(entry.get("summary", "")),
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "tags": [],
            "posted_at": published,
            "is_remote": True,
        })
    return results


_SERPER_DATE_MAP = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}


async def _fetch_serper_post(
    keyword: str,
    location: str,
    client: httpx.AsyncClient,
    date_posted: Optional[str] = None,
) -> list[dict]:
    if not getattr(settings, "serper_api_key", None):
        raise RuntimeError("SERPER_API_KEY not configured")

    body: dict = {"q": keyword, "location": location, "num": 10}
    if date_posted and date_posted in _SERPER_DATE_MAP:
        body["tbs"] = _SERPER_DATE_MAP[date_posted]

    response = await client.post(
        "https://google.serper.dev/jobs",
        json=body,
        headers={
            "X-API-KEY": settings.serper_api_key,
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()

    if len(response.content) > 2 * 1024 * 1024:
        raise ValueError("Serper response exceeded 2 MB size cap")

    payload = response.json()
    results = []
    for j in payload.get("jobs", []):
        # Parse extensions: ["Full-time", "3 days ago", "$120K–$160K a year"]
        extensions = j.get("extensions") or []
        job_type = next((e for e in extensions if any(t in e.lower() for t in ["time", "contract", "intern"])), None)
        date_posted = next((e for e in extensions if "ago" in e.lower() or "today" in e.lower() or "hour" in e.lower()), None)
        salary = next((e for e in extensions if any(c in e for c in ["$", "£", "€", "k", "K"])), None)

        results.append({
            "source": "google_jobs",
            "job_url": j.get("link", ""),
            "title": j.get("title", ""),
            "company": j.get("companyName"),
            "location": j.get("location"),
            "description": j.get("description", ""),
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "tags": [t for t in [job_type] if t],
            "posted_at": None,
            "is_remote": "remote" in (j.get("location") or "").lower(),
            # Extra fields surfaced in UI
            "_salary_text": salary,
            "_date_posted": date_posted,
            "_via": j.get("via"),
        })
    return results


async def _fetch_linkedin(keyword: str, location: str, client: httpx.AsyncClient) -> list[dict]:
    """Search Google (via Serper) specifically for LinkedIn job listings."""
    if not getattr(settings, "serper_api_key", None):
        raise RuntimeError("SERPER_API_KEY not configured")

    query = f"{keyword} site:linkedin.com/jobs"
    if location and location.lower() != "remote":
        query += f" {location}"

    response = await client.post(
        "https://google.serper.dev/search",
        json={"q": query, "num": 10},
        headers={
            "X-API-KEY": settings.serper_api_key,
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()

    if len(response.content) > 2 * 1024 * 1024:
        raise ValueError("Serper response exceeded 2 MB size cap")

    payload = response.json()
    results = []
    for r in payload.get("organic", []):
        link = r.get("link", "")
        if "linkedin.com" not in link:
            continue

        # Title is usually "Job Title - Company | LinkedIn" — strip the suffix
        raw_title = r.get("title", "")
        title = raw_title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()

        # Snippet is typically: "Company · Location · X days ago · Job type..."
        snippet = r.get("snippet", "")
        parts = [p.strip() for p in snippet.split("·")]
        company = parts[0] if parts else None
        loc = parts[1] if len(parts) > 1 else location
        date_text = next((p for p in parts if "ago" in p or "day" in p or "hour" in p or "week" in p), None)

        results.append({
            "source": "linkedin",
            "job_url": link,
            "title": title,
            "company": company,
            "location": loc,
            "description": snippet,
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "tags": [],
            "posted_at": None,
            "is_remote": "remote" in (loc or "").lower(),
            "_date_posted": date_text,
            "_via": "LinkedIn",
        })
    return results


async def _fetch_indeed_rss(keyword: str, location: str, client: httpx.AsyncClient) -> list[dict]:
    params = urllib.parse.urlencode({"q": keyword, "l": location, "sort": "date", "limit": 20})
    url = f"https://rss.indeed.com/rss?{params}"
    data = await bounded_get(client, url)
    feed = feedparser.parse(data.decode("utf-8", errors="replace"))
    results = []
    for entry in feed.entries[:20]:
        published = _parse_feedparser_time(entry.get("published_parsed"))
        results.append({
            "source": "indeed_rss",
            "job_url": entry.get("link", ""),
            "title": entry.get("title", ""),
            "company": None,
            "location": location,
            "description": _strip_html(entry.get("summary", "")),
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "tags": [],
            "posted_at": published,
            "is_remote": "remote" in location.lower(),
        })
    return results


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _parse_feedparser_time(t) -> Optional[datetime]:
    if t is None:
        return None
    try:
        return datetime(*t[:6])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main aggregation function
# ---------------------------------------------------------------------------

ALL_SOURCES = ["google_jobs", "linkedin", "adzuna", "remoteok", "arbeitnow", "weworkremotely", "indeed_rss"]


# Maps experience level to keywords appended to the search query
_LEVEL_KEYWORDS = {
    "entry": "entry level",
    "associate": "associate",
    "mid": "mid level",
    "senior": "senior",
    "lead": "lead",
}


async def scrape_jobs(
    keyword: str,
    location: str,
    sources: Optional[list[str]],
    user_id: int,
    db: Session,
    experience_level: Optional[str] = None,
    date_posted: Optional[str] = None,
) -> tuple[list[dict], dict[str, int], dict[str, str]]:
    """
    Fetch jobs from all requested sources in parallel.

    Returns:
        (deduplicated_results, per_source_counts, error_messages)
    """
    active_sources = sources if sources else ALL_SOURCES

    # Build the enriched keyword (e.g. "software engineer senior")
    level_suffix = _LEVEL_KEYWORDS.get(experience_level or "", "")
    enriched_keyword = f"{keyword} {level_suffix}".strip() if level_suffix else keyword

    source_fetchers = {
        "google_jobs": lambda c: _fetch_serper_post(enriched_keyword, location, c, date_posted),
        "linkedin":    lambda c: _fetch_linkedin(enriched_keyword, location, c),
        "adzuna":      lambda c: _fetch_adzuna(enriched_keyword, location, c, date_posted),
        "remoteok":    lambda c: _fetch_remoteok(enriched_keyword, c),
        "arbeitnow":   lambda c: _fetch_arbeitnow(enriched_keyword, c),
        "weworkremotely": lambda c: _fetch_wwr_rss(enriched_keyword, c),
        "indeed_rss":  lambda c: _fetch_indeed_rss(enriched_keyword, location, c),
    }

    task_names = [s for s in active_sources if s in source_fetchers]

    async with _make_client() as client:
        coroutines = [source_fetchers[name](client) for name in task_names]
        raw_results = await asyncio.gather(*coroutines, return_exceptions=True)

    errors: dict[str, str] = {}
    per_source: dict[str, list[dict]] = {}

    for name, outcome in zip(task_names, raw_results):
        if isinstance(outcome, Exception):
            errors[name] = str(outcome)
            per_source[name] = []
        else:
            per_source[name] = outcome

    # Deduplicate across all sources by job_url
    seen_urls: set[str] = set()
    deduplicated: list[dict] = []
    counts: dict[str, int] = {}

    for source_name in task_names:
        jobs = per_source.get(source_name, [])
        count = 0
        for job in jobs:
            url = (job.get("job_url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            job["user_id"] = user_id
            deduplicated.append(job)
            count += 1
        counts[source_name] = count

    # Persist to DB cache
    _upsert_scraped_jobs(deduplicated, db)

    return deduplicated, counts, errors


# ---------------------------------------------------------------------------
# DB persistence (upsert by job_url + user_id)
# ---------------------------------------------------------------------------

def _upsert_scraped_jobs(jobs: list[dict], db: Session) -> None:
    from models import ScrapedJob

    for j in jobs:
        url = j.get("job_url", "").strip()
        if not url:
            continue
        existing = (
            db.query(ScrapedJob)
            .filter(ScrapedJob.job_url == url, ScrapedJob.user_id == j["user_id"])
            .first()
        )
        if existing:
            existing.fetched_at = datetime.utcnow()
        else:
            tags_raw = j.get("tags") or []
            db.add(
                ScrapedJob(
                    user_id=j["user_id"],
                    source=j["source"],
                    job_url=url,
                    title=j["title"],
                    company=j.get("company"),
                    location=j.get("location"),
                    description=j.get("description"),
                    salary_min=j.get("salary_min"),
                    salary_max=j.get("salary_max"),
                    currency=j.get("currency"),
                    tags=json.dumps(tags_raw),
                    posted_at=j.get("posted_at"),
                    is_remote=bool(j.get("is_remote", False)),
                )
            )
    try:
        db.commit()
    except Exception:
        db.rollback()