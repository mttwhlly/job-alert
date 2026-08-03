from dataclasses import dataclass
from typing import Optional

# remote_status values:
#   "remote"    - ATS data confirms this is a remote posting
#   "onsite"    - ATS data confirms this is not remote
#   "ambiguous" - ATS data doesn't give a confident answer either way


@dataclass
class Job:
    """Normalized job posting, regardless of source ATS."""

    ats: str
    company_slug: str
    company_name: str
    job_id: str
    title: str
    url: str
    location_text: str
    remote_status: str
    posted_at: Optional[str]
    description_text: str

    @property
    def key(self) -> str:
        """Stable identifier used for the seen-jobs store."""
        return f"{self.ats}:{self.company_slug}:{self.job_id}"
