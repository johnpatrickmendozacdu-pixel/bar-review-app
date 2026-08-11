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


def validate_item(item: dict, index: dict, cutoff: datetime.date) -> None:
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

        quote = _normalise(str(authority.get("quote", "")))
        if len(quote) < MIN_QUOTE_LENGTH:
            fail(f"quote for {doc_id} is too short to prove grounding: {quote!r}")
        if quote not in _normalise(entry["text"]):
            fail(
                f"quote for {doc_id} was not found verbatim in the corpus: "
                f"{quote[:60]!r}"
            )


def validate_bank(items, index, cutoff):
    """Return (valid_items, error_messages). Bad items are dropped, not fixed."""
    valid = []
    errors = []

    counts = collections.Counter(i.get("id") for i in items)
    for item_id, n in counts.items():
        if n > 1:
            errors.append(f"{item_id}: duplicate id appears {n} times")

    for item in items:
        try:
            validate_item(item, index, cutoff)
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        valid.append(item)

    return valid, errors
