"""Greenhouse public job board API.

Docs/shape: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
Greenhouse gives no explicit remote flag - only a free-text `location.name` -
so remote status is inferred from that text. Anything not clearly remote or
clearly onsite (hybrid/flexible/blank) is left ambiguous rather than dropped.
"""

import requests

from src.adapters.base import Job
from src.htmlutil import strip_html

API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def _remote_status(location_text: str) -> str:
    lower = (location_text or "").strip().lower()
    if "hybrid" in lower or "flexible" in lower or not lower:
        return "ambiguous"
    if "remote" in lower:
        return "remote"
    return "onsite"


def fetch_jobs(slug: str, company_name: str) -> list:
    resp = requests.get(API_URL.format(slug=slug), params={"content": "true"}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for raw in data.get("jobs", []):
        location_text = (raw.get("location") or {}).get("name", "")
        jobs.append(
            Job(
                ats="greenhouse",
                company_slug=slug,
                company_name=company_name,
                job_id=str(raw["id"]),
                title=raw.get("title", ""),
                url=raw.get("absolute_url", ""),
                location_text=location_text,
                remote_status=_remote_status(location_text),
                posted_at=raw.get("first_published") or raw.get("updated_at"),
                description_text=strip_html(raw.get("content", "")),
            )
        )
    return jobs
