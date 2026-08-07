"""Mayo Clinic - Oracle Cloud Recruiting (Oracle ORC), scoped adapter.

Unlike every other adapter here, this one does NOT fetch a company's whole
board. Mayo Clinic's board has 1,400+ open postings, the overwhelming
majority clinical roles (nursing, patient care) with no interest to this
tool, and Oracle ORC only returns description text via a per-job detail
call - fetching all of it every run would mean well over a thousand HTTP
requests an hour for almost no signal.

Instead this is hardcoded to the two things actually wanted:
  - Jacksonville, FL postings (server-side location filter - complete,
    reliable: every open Jacksonville req is `locationId=300000006415492`).
  - Best-effort "remote" postings, found via Oracle's free-text `keyword`
    search for the literal word "remote". This is NOT a real remote-only
    filter - Oracle ORC exposes no working server-side filter for its
    "Remote worker" custom field, so this misses any fully-remote posting
    that doesn't say "remote" somewhere in its title/description, and can
    also pull in false positives (e.g. a role that just mentions "remote
    patient monitoring"). False positives are cheap: each candidate gets
    the real per-job "Remote worker" field checked below, so anything
    that isn't actually remote/hybrid gets tagged "onsite" and dropped by
    main.py's normal onsite filter. Missed true remote postings are the
    real, unrecoverable gap.

Tech/AI relevance is not filtered here at all - that's the normal job of
config/keywords.yaml, applied generically by main.py to whatever this
adapter returns.
"""

import requests

from src.adapters.base import Job
from src.htmlutil import strip_html

HOST = "https://fa-euwp-saasfaprod1.fa.ocs.oraclecloud.com"
LIST_URL = f"{HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
DETAIL_URL = f"{HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
JOB_PAGE_URL = f"{HOST}/hcmUI/CandidateExperience/en/sites/Mayo-US/job/{{job_id}}"

SITE_NUMBER = "CX_1"
JACKSONVILLE_LOCATION_ID = "300000006415492"
REMOTE_KEYWORD = "Remote"
PAGE_SIZE = 100

_HEADERS = {"User-Agent": "Mozilla/5.0"}

_REMOTE_STATUS_BY_VALUE = {
    "100% remote work": "remote",
    "flexibility of both remote and on-site work": "ambiguous",
    "100% on-site": "onsite",
}


def _list_page(finder_extra: str, offset: int) -> dict:
    params = {
        "onlyData": "true",
        "expand": "requisitionList.secondaryLocations",
        "finder": f"findReqs;siteNumber={SITE_NUMBER},limit={PAGE_SIZE},offset={offset},{finder_extra}",
    }
    resp = requests.get(LIST_URL, params=params, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["items"][0]


def _list_all(finder_extra: str) -> list:
    items = []
    offset = 0
    while True:
        page = _list_page(finder_extra, offset)
        items.extend(page.get("requisitionList", []))
        offset += PAGE_SIZE
        if offset >= page["TotalJobsCount"]:
            break
    return items


def _fetch_detail(job_id: str) -> dict:
    params = {
        "onlyData": "true",
        "expand": "all",
        "finder": f'ById;Id="{job_id}",siteNumber={SITE_NUMBER}',
    }
    resp = requests.get(DETAIL_URL, params=params, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["items"][0]


def _remote_status(detail: dict) -> str:
    for field in detail.get("requisitionFlexFields") or []:
        if field.get("Prompt") == "Remote worker":
            value = (field.get("Value") or "").strip().lower()
            return _REMOTE_STATUS_BY_VALUE.get(value, "ambiguous")
    return "ambiguous"


def _description_text(detail: dict) -> str:
    parts = [
        detail.get("ExternalDescriptionStr"),
        detail.get("ExternalQualificationsStr"),
        detail.get("ExternalResponsibilitiesStr"),
    ]
    return "\n".join(strip_html(part) for part in parts if part)


def fetch_jobs(slug: str, company_name: str) -> list:
    candidates = {}
    for item in _list_all(f"locationId={JACKSONVILLE_LOCATION_ID}"):
        candidates[item["Id"]] = item
    for item in _list_all(f"keyword={REMOTE_KEYWORD}"):
        candidates.setdefault(item["Id"], item)

    jobs = []
    for job_id, item in candidates.items():
        detail = _fetch_detail(job_id)
        jobs.append(
            Job(
                ats="mayo_clinic",
                company_slug=slug,
                company_name=company_name,
                job_id=str(job_id),
                title=item.get("Title", ""),
                url=JOB_PAGE_URL.format(job_id=job_id),
                location_text=item.get("PrimaryLocation", ""),
                remote_status=_remote_status(detail),
                posted_at=detail.get("ExternalPostedStartDate") or item.get("PostedDate"),
                description_text=_description_text(detail),
            )
        )
    return jobs
