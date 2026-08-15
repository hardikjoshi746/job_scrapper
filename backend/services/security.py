"""
Security utilities for the job scraper feature.
Handles: input sanitization, URL allowlisting, SSRF prevention, robots.txt compliance,
and content-size enforcement.
"""

import re
import html
import json
import asyncio
import ipaddress
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Optional
import httpx
from fastapi import Request


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_KEYWORD_LEN = 100
MAX_LOCATION_LEN = 100
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB
REQUEST_TIMEOUT = 15.0  # seconds

# Only these domains may be fetched by the scraper
ALLOWED_DOMAINS: set[str] = {
    "api.adzuna.com",
    "remoteok.com",
    "www.arbeitnow.com",
    "weworkremotely.com",
    "rss.indeed.com",
    "www.indeed.com",
    "google.serper.dev",
}

# Private/loopback ranges — block SSRF attempts
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Cache robots.txt per origin for the process lifetime
_robots_cache: dict[str, Optional[RobotFileParser]] = {}
_robots_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Input sanitization
# ---------------------------------------------------------------------------

def sanitize_text(value: str, max_len: int = MAX_KEYWORD_LEN) -> str:
    """Strip HTML tags, decode HTML entities, collapse whitespace, enforce length."""
    if not isinstance(value, str):
        raise ValueError("Input must be a string")
    value = _HTML_TAG_RE.sub("", value)
    value = html.unescape(value)
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)  # remove control chars
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > max_len:
        raise ValueError(f"Input too long — maximum {max_len} characters allowed")
    if not value:
        raise ValueError("Input cannot be empty")
    return value


# ---------------------------------------------------------------------------
# URL validation & SSRF prevention
# ---------------------------------------------------------------------------

def _is_private_ip(host: str) -> bool:
    """Return True if host resolves to a private/loopback address."""
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        # Not a raw IP — we rely on the allowlist to block internal hostnames
        return False


def validate_url(url: str) -> str:
    """
    Validate a URL against the security policy:
      1. Scheme must be https://
      2. Host must be in ALLOWED_DOMAINS (exact or subdomain)
      3. If host is a raw IP, it must not be in a private range (SSRF prevention)

    Returns the validated URL, or raises ValueError on violation.
    """
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are permitted (got {parsed.scheme!r})")

    host = (parsed.netloc or "").lower().split(":")[0]
    if not host:
        raise ValueError("URL has no host")

    # SSRF: block raw private IPs immediately
    if _is_private_ip(host):
        raise ValueError(f"Requests to private IP addresses are not permitted: {host}")

    # Allowlist check
    in_allowlist = any(
        host == domain or host.endswith("." + domain)
        for domain in ALLOWED_DOMAINS
    )
    if not in_allowlist:
        raise ValueError(f"Domain {host!r} is not in the approved allowlist")

    return url


# ---------------------------------------------------------------------------
# Robots.txt compliance
# ---------------------------------------------------------------------------

APP_USER_AGENT = "JobHuntAI/1.0 (+https://jobhunt.ai; contact@jobhunt.ai)"


async def is_scraping_allowed(url: str) -> bool:
    """
    Check whether scraping the given URL is permitted by the site's robots.txt.
    Results are cached per origin for the lifetime of the process.
    Returns True (allowed) by default when robots.txt is unreachable.
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    async with _robots_lock:
        if origin not in _robots_cache:
            robots_url = f"{origin}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(robots_url, follow_redirects=True)
                    rp.parse(resp.text.splitlines())
                _robots_cache[origin] = rp
            except Exception:
                # Fail open: if we can't read robots.txt, assume allowed
                _robots_cache[origin] = None

    rp = _robots_cache.get(origin)
    if rp is None:
        return True
    return rp.can_fetch(APP_USER_AGENT, url)


# ---------------------------------------------------------------------------
# Size-capped HTTP fetching
# ---------------------------------------------------------------------------

async def bounded_get(client: httpx.AsyncClient, url: str, **kwargs) -> bytes:
    """
    Perform a GET request and return the response body, aborting if it exceeds
    MAX_RESPONSE_BYTES (2 MB). Raises httpx.HTTPStatusError on 4xx/5xx.
    """
    async with client.stream("GET", url, **kwargs) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes(chunk_size=65536):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"Response from {url!r} exceeded the 2 MB size limit — aborting"
                )
            chunks.append(chunk)
        return b"".join(chunks)


# ---------------------------------------------------------------------------
# Rate-limit key function (used by slowapi)
# ---------------------------------------------------------------------------

def get_user_key(request: Request) -> str:
    """
    Identify the caller for rate limiting.
    Prefers JWT user_id (decoded from Authorization header) over IP address.
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if token:
        try:
            from jose import jwt
            from config import settings
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            sub = payload.get("sub") or payload.get("user_id")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return f"ip:{request.client.host if request.client else 'unknown'}"