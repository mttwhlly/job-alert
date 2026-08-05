"""Poll every company in config/companies.yaml, match new postings against
config/keywords.yaml, and open a GitHub issue for each new match.

Run locally for a dry run (no GITHUB_TOKEN needed, issues print instead of
being created):

    python main.py

Environment:
    GITHUB_TOKEN        - set automatically in GitHub Actions
    GITHUB_REPOSITORY   - set automatically in GitHub Actions
"""

from pathlib import Path

import yaml

from src import matcher, notify
from src.adapters import ashby, greenhouse, lever, rippling, smartrecruiters, workable
from src.store import SeenStore

ROOT = Path(__file__).parent
CONFIG_DIR = ROOT / "config"
SEEN_STORE_PATH = ROOT / "data" / "seen.json"

ADAPTERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workable": workable.fetch_jobs,
    "smartrecruiters": smartrecruiters.fetch_jobs,
    "rippling": rippling.fetch_jobs,
}


def load_yaml(name: str):
    with (CONFIG_DIR / name).open() as f:
        return yaml.safe_load(f)


def main():
    companies = load_yaml("companies.yaml")["companies"]
    rules = matcher.load_rules(load_yaml("keywords.yaml")["rules"])
    store = SeenStore(SEEN_STORE_PATH)

    new_count = 0
    for company in companies:
        ats = company["ats"]
        fetch = ADAPTERS.get(ats)
        if fetch is None:
            print(f"skipping {company['name']}: no adapter registered for ats={ats!r}")
            continue

        try:
            jobs = fetch(company["slug"], company["name"])
        except Exception as exc:  # noqa: BLE001 - one bad board shouldn't kill the run
            print(f"error fetching {company['name']} ({ats}): {exc}")
            continue

        for job in jobs:
            if not store.is_new(job.key):
                continue

            matched = matcher.match(job.title, job.description_text, rules)
            if not matched:
                store.mark_seen(job.key, job.title, job.company_name)
                continue

            if job.remote_status == "onsite":
                store.mark_seen(job.key, job.title, job.company_name)
                continue

            print(f"NEW MATCH [{job.remote_status}] {job.company_name}: {job.title}")
            notify.create_issue(job, matched)
            store.mark_seen(job.key, job.title, job.company_name)
            new_count += 1

    store.save()
    print(f"done. {new_count} new match(es).")


if __name__ == "__main__":
    main()
