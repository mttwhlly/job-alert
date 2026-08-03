"""Workable public jobs widget API.

Docs/shape: https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
The `details=true` param is required to get each job's HTML description -
without it the endpoint only returns title/metadata, no description text.
`telecommuting` is an explicit boolean set by the company, so it's trusted
directly rather than treated as ambiguous.
"""

import requests

from src.adapters.base import Job
from src.htmlutil import strip_html

API_URL = "https://apply.workable.com/api/v1/widget/accounts/{slug}"


def _remote_status(raw: dict) -> str:
    return "remote" if raw.get("telecommuting") else "onsite"


def _location_text(raw: dict) -> str:
    parts = [raw.get("city", ""), raw.get("state", ""), raw.get("country", "")]
    return ", ".join(p for p in parts if p)


def fetch_jobs(slug: str, company_name: str) -> list:
    resp = requests.get(API_URL.format(slug=slug), params={"details": "true"}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for raw in data.get("jobs", []):
        jobs.append(
            Job(
                ats="workable",
                company_slug=slug,
                company_name=company_name,
                job_id=raw.get("shortcode", ""),
                title=raw.get("title", ""),
                url=raw.get("url", ""),
                location_text=_location_text(raw),
                remote_status=_remote_status(raw),
                posted_at=raw.get("published_on"),
                description_text=strip_html(raw.get("description", "")),
            )
        )
    return jobs
