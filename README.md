# job-alert

Polls company job boards directly via their ATS's public JSON APIs (Greenhouse,
Lever, Ashby, Workable, SmartRecruiters) and opens a GitHub Issue for each new
posting that matches a keyword list. Runs hourly via GitHub Actions, no
external services or secrets required.

This exists instead of email digests / Google Alerts because those lag by
days; polling the ATS APIs directly surfaces postings within an hour.

## How it works

1. `main.py` reads `config/companies.yaml` (the watchlist) and
   `config/keywords.yaml` (the match rules).
2. For each company, the adapter for its ATS (`src/adapters/`) fetches current
   postings and normalizes them into a common `Job` shape.
3. Postings already recorded in `data/seen.json` are skipped.
4. Remaining postings are checked against the keyword rules. Matches that
   aren't confirmed non-remote get a GitHub Issue opened for them (see
   "Remote filtering" below).
5. Every fetched posting - matched or not - is recorded in `data/seen.json` so
   it's never re-alerted. The GitHub Actions workflow commits this file back
   to the repo after each run.

## Adding a company

Add one line to `config/companies.yaml`:

```yaml
- { name: "Display Name", ats: <greenhouse|lever|ashby|workable|smartrecruiters>, slug: <slug> }
```

Find the slug from the company's careers page URL:

| ATS | Careers URL pattern | slug |
|---|---|---|
| Greenhouse | `job-boards.greenhouse.io/<slug>` | that path segment |
| Lever | `jobs.lever.co/<slug>` | that path segment |
| Ashby | `jobs.ashbyhq.com/<slug>` | that path segment |
| Workable | `apply.workable.com/<slug>` | that path segment |
| SmartRecruiters | `careers.smartrecruiters.com/<slug>` | that path segment |

Note on SmartRecruiters: the public postings API is opt-in per company, so a
given slug may 404 even if the careers page above is real. If that happens
the run logs `error fetching <company> (smartrecruiters): ...` and continues
with the rest of the watchlist rather than failing.

## Tuning keywords

`config/keywords.yaml` rules are matched (case-insensitive) against each
job's title + description. A plain string matches if that phrase appears
anywhere. An `all_of` rule matches only if every phrase in its list appears -
used for compound signals, e.g. requiring both "frontend engineer" and "ai":

```yaml
rules:
  - design systems
  - all_of: [frontend engineer, ai]
```

Add, remove, or narrow rules as alerts come in.

## Remote filtering

Each adapter maps ATS-specific remote data to one of three states:

- **`remote`** - confirmed remote by explicit ATS data (Ashby `isRemote`,
  Lever `workplaceType`, Workable `telecommuting`, SmartRecruiters
  `location.remote`) or, for Greenhouse (which has no structured remote
  field), a location string containing "remote".
- **`onsite`** - confirmed not remote. These are recorded as seen but never
  alerted.
- **`ambiguous`** - the ATS data doesn't give a confident answer (e.g. hybrid
  postings, or Greenhouse postings whose location text doesn't clearly say
  either way). These **are still alerted**, not dropped, but their GitHub
  Issue title is prefixed `[REMOTE UNCLEAR]` and tagged with the
  `remote-unclear` label so you can judge them yourself.

## Notifications

Each new match opens a GitHub Issue labeled `job-alert` (plus `remote-unclear`
when applicable) with the company, location, remote status, matched
keywords, and a link to the posting. Watch this repo (or just the
`job-alert` label) to get GitHub's own notifications - no other setup
needed.

## Running locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Without `GITHUB_TOKEN`/`GITHUB_REPOSITORY` set (both are set automatically in
GitHub Actions), matches print to stdout instead of creating real issues, so
it's safe to run repeatedly while testing.

## Schedule

`.github/workflows/poll.yml` runs hourly (`0 * * * *`) and can also be
triggered manually from the Actions tab. It needs no repo secrets - it uses
the default `GITHUB_TOKEN` GitHub Actions provides to every workflow run.
