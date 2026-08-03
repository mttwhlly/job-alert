import json
from datetime import datetime, timezone
from pathlib import Path


class SeenStore:
    """Tracks job keys we've already alerted on, persisted as a JSON file."""

    def __init__(self, path: Path):
        self.path = path
        if path.exists():
            with path.open() as f:
                self._seen = json.load(f)
        else:
            self._seen = {}

    def is_new(self, key: str) -> bool:
        return key not in self._seen

    def mark_seen(self, key: str, title: str, company: str) -> None:
        self._seen[key] = {
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "company": company,
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as f:
            json.dump(self._seen, f, indent=2, sort_keys=True)
            f.write("\n")
