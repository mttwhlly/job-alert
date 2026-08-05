"""Keyword matching against job title + description text.

Rules come from config/keywords.yaml. A plain string rule matches if that
phrase appears anywhere (title or description). An `all_of` rule matches
only if every phrase in its list matches - each entry can be a plain string
(matched anywhere) or `{ phrase: ..., in: title }` to restrict that one
phrase to the job title, e.g. requiring "frontend engineer" in the title
so a role doesn't match just because it mentions collaborating with
frontend engineers.

Matching ignores hyphens (in addition to case), so a rule written as
"frontend engineer" also catches "front-end engineer". Phrases are matched
on word boundaries so "product engineer" doesn't fire inside "product
engineering".
"""

import re


def _normalize(text: str) -> str:
    return text.lower().replace("-", "")


def _phrase_pattern(phrase: str) -> "re.Pattern":
    # Trailing s? allows plurals ("product engineers") without also matching
    # unrelated continuations like "product engineering".
    return re.compile(r"\b" + re.escape(phrase) + r"s?\b")


def _load_entry(entry):
    """Return (label, pattern, scope) for one all_of list item."""
    if isinstance(entry, str):
        return entry, _phrase_pattern(_normalize(entry)), "any"
    if isinstance(entry, dict) and "phrase" in entry:
        scope = entry.get("in", "any")
        if scope not in ("any", "title"):
            raise ValueError(f"Unrecognized phrase scope: {scope!r}")
        return entry["phrase"], _phrase_pattern(_normalize(entry["phrase"])), scope
    raise ValueError(f"Unrecognized phrase entry: {entry!r}")


def load_rules(raw_rules):
    normalized = []
    for rule in raw_rules:
        if isinstance(rule, str):
            normalized.append((rule, [(_phrase_pattern(_normalize(rule)), "any")]))
        elif isinstance(rule, dict) and "all_of" in rule:
            entries = [_load_entry(e) for e in rule["all_of"]]
            label = " + ".join(e[0] for e in entries)
            normalized.append((label, [(e[1], e[2]) for e in entries]))
        else:
            raise ValueError(f"Unrecognized keyword rule: {rule!r}")
    return normalized


def match(title: str, description: str, rules) -> list:
    """Return the labels of every rule that matches the given title/description."""
    title_haystack = _normalize(title)
    full_haystack = _normalize(f"{title}\n{description}")

    matched = []
    for label, entries in rules:
        if all(
            pattern.search(title_haystack if scope == "title" else full_haystack)
            for pattern, scope in entries
        ):
            matched.append(label)
    return matched
