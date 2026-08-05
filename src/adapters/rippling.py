"""Rippling ATS - unofficial, scraped adapter.

Rippling has no documented public API. This works by parsing the
`__NEXT_DATA__` JSON that Rippling's job board pages embed to render
themselves server-side - the same data the page needs to display, just
read directly instead of rendering it.

Known limitations (accepted tradeoff, see README):
  - The board listing page only preloads the first ~20 postings (page 0
    of its internal pagination). Boards larger than that will be
    under-counted.
  - This is reverse-engineered from page structure, not a stable contract.
    If Rippling changes their frontend, this can silently start returning
    nothing - there's no versioned API to depend on instead.
"""

import json
import re

import requests

from src.adapters.base import Job
from src.htmlutil import strip_html

BOARD_URL = "https://ats.rippling.com/{slug}/jobs"
DETAIL_URL = "https://ats.rippling.com/{slug}/jobs/{job_id}"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


def _next_data(html: str) -> dict:
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise ValueError("__NEXT_DATA__ not found - Rippling page structure may have changed")
    return json.loads(match.group(1))


def _list_postings(slug: str) -> list:
    resp = requests.get(BOARD_URL.format(slug=slug), timeout=30)
    resp.raise_for_status()
    data = _next_data(resp.text)

    queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
    for query in queries:
        key = query.get("queryKey", [])
        if len(key) >= 3 and key[0] == "board" and key[2] == "job-posts":
            return query["state"]["data"].get("items", [])
    return []


def _remote_status(locations: list) -> str:
    types = {(loc.get("workplaceType") or "").upper() for loc in locations}
    if "REMOTE" in types:
        return "remote"
    if "HYBRID" in types:
        return "ambiguous"
    if types and types != {""}:
        return "onsite"
    return "ambiguous"


def _fetch_detail(slug: str, job_id: str) -> dict:
    resp = requests.get(DETAIL_URL.format(slug=slug, job_id=job_id), timeout=30)
    resp.raise_for_status()
    data = _next_data(resp.text)
    return data["props"]["pageProps"]["apiData"]["jobPost"]


def _description_text(job_post: dict) -> str:
    sections = job_post.get("description") or {}
    parts = [strip_html(html) for html in sections.values() if html]
    return "\n".join(parts)


def fetch_jobs(slug: str, company_name: str) -> list:
    jobs = []
    for item in _list_postings(slug):
        job_post = _fetch_detail(slug, item["id"])
        locations = item.get("locations") or []

        jobs.append(
            Job(
                ats="rippling",
                company_slug=slug,
                company_name=company_name,
                job_id=str(item["id"]),
                title=item.get("name", ""),
                url=item.get("url", ""),
                location_text=", ".join(loc.get("name", "") for loc in locations if loc),
                remote_status=_remote_status(locations),
                posted_at=job_post.get("createdOn"),
                description_text=_description_text(job_post),
            )
        )
    return jobs
