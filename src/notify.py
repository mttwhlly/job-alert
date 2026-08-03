"""Notification via GitHub Issues.

Falls back to printing the issue to stdout ("dry run") when GITHUB_TOKEN /
GITHUB_REPOSITORY aren't set, so this works fine when run locally.
"""

import os

import requests

from src.adapters.base import Job


def create_issue(job: Job, matched_keywords: list) -> None:
    title_prefix = "[REMOTE UNCLEAR] " if job.remote_status == "ambiguous" else ""
    title = f"{title_prefix}{job.company_name}: {job.title}"

    body = "\n".join(
        [
            f"**Company:** {job.company_name}",
            f"**Location:** {job.location_text or 'unspecified'}",
            f"**Remote status:** {job.remote_status}",
            f"**Matched keywords:** {', '.join(matched_keywords)}",
            f"**Posted:** {job.posted_at or 'unknown'}",
            "",
            f"[View posting]({job.url})",
        ]
    )

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        print("--- DRY RUN (no GITHUB_TOKEN/GITHUB_REPOSITORY set) ---")
        print(title)
        print(body)
        print("---")
        return

    labels = ["job-alert"]
    if job.remote_status == "ambiguous":
        labels.append("remote-unclear")

    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"title": title, "body": body, "labels": labels},
        timeout=15,
    )
    resp.raise_for_status()
