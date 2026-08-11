"""The gate that makes "accurate or it isn't asked" mechanical.

Nothing here trusts an author's good intentions. Every claim an item makes
about the law is checked against the corpus text itself.
"""

import collections
import datetime
import json
import pathlib

TYPES = frozenset({"hypothetical", "issue_spotting", "essay", "doctrine"})
SUBJECTS = frozenset(
    {"remedial", "civil", "commercial_tax", "political", "labor", "criminal"}
)

# Shorter than this and a "quote" is a common phrase that would appear in any
# legal text — it proves nothing about grounding.
MIN_QUOTE_LENGTH = 20

# "controlling" governs the answer; "related" is a similar case offered for
# context. Both are validated identically — a related case is a real corpus
# document with a real verbatim quote, so its link and its text are as
# trustworthy as the controlling authority's.
ROLES = frozenset({"controlling", "related"})
DEFAULT_ROLE = "controlling"


class ValidationError(Exception):
    """An item failed a check and must not be shipped."""


def _normalise(text: str) -> str:
    """Collapse whitespace so line wrapping does not defeat a real quote."""
    return " ".join(text.split())


def build_index(corpus_dir) -> dict:
    """Map every document and provision id to its text and date."""
    corpus_dir = pathlib.Path(corpus_dir)
    index = {}
    for name in ("statute.json", "case.json", "provisions.json"):
        path = corpus_dir / name
        if not path.exists():
            continue
        for doc in json.loads(path.read_text(encoding="utf-8")):
            index[doc["id"]] = {
                "text": doc["text"],
                "promulgation_date": datetime.date.fromisoformat(
                    doc["promulgation_date"]
                ),
            }
    return index


def load_superseded(path) -> dict:
    """Provisions whose corpus text is no longer current.

    The corpus holds ORIGINAL enacted texts, so a verbatim quote can still be
    superseded law — the RPC's estafa amounts read as they did in 1930. This
    registry is the mechanical half of currency checking; the judgment half
    lives in the verifying-legal-currency skill.
    """
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    return {
        k: v
        for k, v in json.loads(path.read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }


def validate_item(
    item: dict, index: dict, cutoff: datetime.date, superseded: dict | None = None
) -> None:
    superseded = superseded or {}
    item_id = item.get("id", "<no id>")

    def fail(message):
        raise ValidationError(f"{item_id}: {message}")

    if item.get("type") not in TYPES:
        fail(f"type {item.get('type')!r} not in {sorted(TYPES)}")
    if item.get("subject") not in SUBJECTS:
        fail(f"subject {item.get('subject')!r} not in {sorted(SUBJECTS)}")
    if not str(item.get("question", "")).strip():
        fail("question must not be empty")
    if not str(item.get("answer_key", "")).strip():
        fail("answer_key must not be empty")
    if item.get("difficulty") not in (1, 2, 3):
        fail(f"difficulty {item.get('difficulty')!r} must be 1, 2 or 3")

    authorities = item.get("authorities") or []
    if not authorities:
        fail("must cite at least one authority")

    roles = [a.get("role", DEFAULT_ROLE) for a in authorities]
    for role in roles:
        if role not in ROLES:
            fail(f"authority role {role!r} not in {sorted(ROLES)}")
    if DEFAULT_ROLE not in roles:
        fail("must cite at least one controlling authority; something has to govern")

    for authority in authorities:
        doc_id = authority.get("doc_id")
        if doc_id not in index:
            fail(f"cited document {doc_id!r} is not in the corpus")

        entry = index[doc_id]
        if entry["promulgation_date"] > cutoff:
            fail(
                f"{doc_id} is dated {entry['promulgation_date']}, "
                f"after the coverage cut-off {cutoff}"
            )

        # Currency: quoting amended law verbatim still misstates the law.
        flagged = superseded.get(doc_id)
        if flagged and role_of(authority) == DEFAULT_ROLE:
            required = flagged.get("replaced_by") or []
            cited = {a.get("doc_id") for a in authorities}
            missing = [r for r in required if r not in cited]
            if missing:
                fail(
                    f"{doc_id} is superseded ({flagged['reason']}) and the item does "
                    f"not cite what replaced it: {missing}"
                )

        quote = _normalise(str(authority.get("quote", "")))
        if len(quote) < MIN_QUOTE_LENGTH:
            fail(f"quote for {doc_id} is too short to prove grounding: {quote!r}")
        if quote not in _normalise(entry["text"]):
            fail(
                f"quote for {doc_id} was not found verbatim in the corpus: "
                f"{quote[:60]!r}"
            )


def role_of(authority: dict) -> str:
    return authority.get("role", DEFAULT_ROLE)


def validate_bank(items, index, cutoff, superseded=None):
    """Return (valid_items, error_messages). Bad items are dropped, not fixed."""
    valid = []
    errors = []

    counts = collections.Counter(i.get("id") for i in items)
    for item_id, n in counts.items():
        if n > 1:
            errors.append(f"{item_id}: duplicate id appears {n} times")

    for item in items:
        try:
            validate_item(item, index, cutoff, superseded)
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        valid.append(item)

    return valid, errors
