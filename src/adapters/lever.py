"""Lever public postings API.

Docs/shape: https://api.lever.co/v0/postings/{slug}?mode=json
Lever gives an explicit `workplaceType` field (remote/hybrid/on-site), so
remote status is a direct read. Description content is split across several
free-text sections (opening/description/additional/lists) that companies
fill in inconsistently, so we concatenate all of them for keyword matching.
"""

from datetime import datetime, timezone

import requests

from src.adapters.base import Job
from src.htmlutil import strip_html

API_URL = "https://api.lever.co/v0/postings/{slug}"


def _remote_status(raw: dict) -> str:
    workplace = (raw.get("workplaceType") or "").strip().lower()
    if workplace == "remote":
        return "remote"
    if workplace in ("onsite", "on-site"):
        return "onsite"
    return "ambiguous"


def _description_text(raw: dict) -> str:
    parts = [
        raw.get("openingPlain", ""),
        raw.get("descriptionPlain", ""),
        raw.get("descriptionBodyPlain", ""),
        raw.get("additionalPlain", ""),
    ]
    for item in raw.get("lists", []):
        parts.append(strip_html(item.get("content", "")))
    return "\n".join(p for p in parts if p)


def _location_text(raw: dict) -> str:
    categories = raw.get("categories") or {}
    all_locations = categories.get("allLocations") or []
    if all_locations:
        return ", ".join(all_locations)
    return categories.get("location", "") or ""


def _posted_at(raw: dict):
    created_at = raw.get("createdAt")
    if not created_at:
        return None
    return datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).isoformat()


def fetch_jobs(slug: str, company_name: str) -> list:
    resp = requests.get(API_URL.format(slug=slug), params={"mode": "json"}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for raw in data:
        jobs.append(
            Job(
                ats="lever",
                company_slug=slug,
                company_name=company_name,
                job_id=str(raw["id"]),
                title=raw.get("text", ""),
                url=raw.get("hostedUrl", ""),
                location_text=_location_text(raw),
                remote_status=_remote_status(raw),
                posted_at=_posted_at(raw),
                description_text=_description_text(raw),
            )
        )
    return jobs
