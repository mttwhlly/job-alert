"""SmartRecruiters public postings API.

Docs/shape: https://api.smartrecruiters.com/v1/companies/{slug}/postings
Only available for companies that have opted the public feed in - a 404
here just means this company doesn't expose it (handled by the caller,
which logs and skips a failing company rather than crashing the run).

This is a two-tier API: the list endpoint has no description text or public
URL, so a detail call is made per posting to fill those in. `location.remote`
/ `location.hybrid` are explicit booleans set by the company.
"""

import requests

from src.adapters.base import Job
from src.htmlutil import strip_html

LIST_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
DETAIL_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{posting_id}"
PAGE_SIZE = 100


def _remote_status(location: dict) -> str:
    if location.get("remote") is True:
        return "remote"
    if location.get("hybrid") is True:
        return "ambiguous"
    if not location:
        return "ambiguous"
    return "onsite"


def _list_postings(slug: str) -> list:
    postings = []
    offset = 0
    while True:
        resp = requests.get(
            LIST_URL.format(slug=slug),
            params={"limit": PAGE_SIZE, "offset": offset},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        postings.extend(data.get("content", []))
        offset += PAGE_SIZE
        if offset >= data.get("totalFound", 0):
            break
    return postings


def _description_text(detail: dict) -> str:
    sections = (detail.get("jobAd") or {}).get("sections") or {}
    parts = [strip_html(section.get("text", "")) for section in sections.values()]
    return "\n".join(p for p in parts if p)


def fetch_jobs(slug: str, company_name: str) -> list:
    jobs = []
    for raw in _list_postings(slug):
        detail_resp = requests.get(
            DETAIL_URL.format(slug=slug, posting_id=raw["id"]), timeout=30
        )
        detail_resp.raise_for_status()
        detail = detail_resp.json()

        location = raw.get("location") or {}
        jobs.append(
            Job(
                ats="smartrecruiters",
                company_slug=slug,
                company_name=company_name,
                job_id=str(raw["id"]),
                title=raw.get("name", ""),
                url=detail.get("postingUrl", ""),
                location_text=location.get("fullLocation", ""),
                remote_status=_remote_status(location),
                posted_at=raw.get("releasedDate"),
                description_text=_description_text(detail),
            )
        )
    return jobs
