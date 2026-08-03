"""Ashby public job board API.

Docs/shape: https://api.ashbyhq.com/posting-api/job-board/{slug}
Ashby gives explicit `isRemote` and `workplaceType` fields, so remote status
is a direct read rather than a text heuristic (unlike Greenhouse).
"""

import requests

from src.adapters.base import Job

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def _remote_status(raw: dict) -> str:
    if raw.get("isRemote") is True:
        return "remote"
    workplace = (raw.get("workplaceType") or "").strip().lower()
    if workplace == "onsite":
        return "onsite"
    return "ambiguous"


def fetch_jobs(slug: str, company_name: str) -> list:
    resp = requests.get(API_URL.format(slug=slug), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for raw in data.get("jobs", []):
        secondary = [
            loc.get("location", "") for loc in raw.get("secondaryLocations", []) if loc
        ]
        locations = [raw.get("location", "")] + secondary
        location_text = ", ".join(loc for loc in locations if loc)

        jobs.append(
            Job(
                ats="ashby",
                company_slug=slug,
                company_name=company_name,
                job_id=str(raw["id"]),
                title=raw.get("title", ""),
                url=raw.get("jobUrl", ""),
                location_text=location_text,
                remote_status=_remote_status(raw),
                posted_at=raw.get("publishedAt"),
                description_text=raw.get("descriptionPlain", ""),
            )
        )
    return jobs
