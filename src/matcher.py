"""Keyword matching against job title + description text.

Rules come from config/keywords.yaml. A plain string rule matches if that
phrase appears in the text. An `all_of` rule matches only if every phrase
in its list appears (for compound signals like "frontend engineer" + "ai").

Matching ignores hyphens (in addition to case), so a rule written as
"frontend engineer" also catches "front-end engineer".
"""


def _normalize(text: str) -> str:
    return text.lower().replace("-", "")


def load_rules(raw_rules):
    normalized = []
    for rule in raw_rules:
        if isinstance(rule, str):
            normalized.append((rule, [_normalize(rule)]))
        elif isinstance(rule, dict) and "all_of" in rule:
            phrases = [_normalize(p) for p in rule["all_of"]]
            normalized.append((" + ".join(rule["all_of"]), phrases))
        else:
            raise ValueError(f"Unrecognized keyword rule: {rule!r}")
    return normalized


def match(text: str, rules) -> list:
    """Return the labels of every rule that matches the given text."""
    haystack = _normalize(text)
    return [label for label, phrases in rules if all(p in haystack for p in phrases)]
