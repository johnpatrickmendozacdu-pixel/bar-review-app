"""The gate that makes "accurate or it isn't asked" mechanical.

Nothing here trusts an author's good intentions. Every claim an item makes
about the law is checked against the corpus text itself.
"""

import collections
import datetime
import difflib
import json
import pathlib

from ingest.shards import read_cases

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

# Document ids for decisions, as opposed to statutory provisions.
CASE_PREFIXES = ("gr-", "am-", "ac-", "bm-")

# A case citation must actually teach the case: who sued whom, what was
# decided, and why. A docket number on its own teaches nothing.
MIN_CONTEXT_LENGTH = 80
DEFAULT_ROLE = "controlling"

# How far two sources may drift before the difference is treated as legal
# rather than cosmetic. "wilfully"/"willfully" and "in manner"/"in a manner"
# fall well under this; a dropped qualifier such as "without a definite period"
# does not.
SIGNIFICANT = 0.06


def divergence(a: str, b: str) -> float:
    """0.0 when two texts say the same thing, 1.0 when unrelated.

    The e-Library and lawphil transcribe the same statutes with small spelling
    and punctuation differences. Those carry no legal weight. A changed
    qualifier, a different provision number, or an added exception does.
    """
    left, right = _loose(a), _loose(b)
    if not left or not right:
        return 1.0
    return 1.0 - difflib.SequenceMatcher(None, left, right).ratio()


def _drift_from(quote: str, reference: str) -> float:
    """How far `quote` drifts from the closest passage in `reference`.

    Returns 0.0 when the passage is present (allowing for case and
    punctuation), rising toward 1.0 as the texts diverge in substance.
    """
    loose_quote, loose_ref = _loose(quote), _loose(reference)
    if not loose_quote or not loose_ref:
        return 1.0
    if loose_quote in loose_ref:
        return 0.0

    # Locate the closest region, then compare a same-length window against it
    # so a short quote is not penalised for the length of the whole statute.
    matcher = difflib.SequenceMatcher(None, loose_quote, loose_ref)
    match = matcher.find_longest_match(0, len(loose_quote), 0, len(loose_ref))
    start = max(0, match.b - match.a)
    window = loose_ref[start : start + len(loose_quote)]
    return divergence(loose_quote, window)


def _loose(text: str) -> str:
    """Lowercased, punctuation-stripped, whitespace-collapsed."""
    return " ".join("".join(c if c.isalnum() else " " for c in text.lower()).split())


class ValidationError(Exception):
    """An item failed a check and must not be shipped."""


def _normalise(text: str) -> str:
    """Collapse whitespace so line wrapping does not defeat a real quote."""
    return " ".join(text.split())


def build_index(corpus_dir) -> dict:
    """Map every document and provision id to its text and date."""
    corpus_dir = pathlib.Path(corpus_dir)
    index = {}
    docs = list(read_cases(corpus_dir))
    for name in ("statute.json", "provisions.json"):
        path = corpus_dir / name
        if path.exists():
            docs.extend(json.loads(path.read_text(encoding="utf-8")))
    for doc in docs:
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


def load_elibrary(path) -> dict:
    """The Supreme Court's own copy of each cited statute, keyed by doc id."""
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


ELIBRARY_HOST = "elibrary.judiciary.gov.ph"


def elibrary_sources(statutes: dict, cases: list) -> dict:
    """The Court's own texts, keyed by document id.

    Statutes are fetched separately by tools/refresh_elibrary.py. Decisions are
    already scraped from the e-Library during ingest, so they are primary text
    already and are merged in here rather than fetched twice.
    """
    sources = dict(statutes)
    for case in cases:
        if ELIBRARY_HOST in case.get("source_url", ""):
            sources[case["id"]] = {"url": case["source_url"], "text": case["text"]}
    return sources


def load_cases(corpus_dir) -> list:
    return read_cases(corpus_dir)


def build_source_urls(corpus_dir) -> dict:
    """doc id -> the URL the corpus actually recorded for it."""
    corpus_dir = pathlib.Path(corpus_dir)
    urls = {doc["id"]: doc["source_url"] for doc in read_cases(corpus_dir)}
    for name in ("statute.json", "provisions.json"):
        path = corpus_dir / name
        if path.exists():
            for doc in json.loads(path.read_text(encoding="utf-8")):
                urls[doc["id"]] = doc["source_url"]
    return urls


def build_parents(corpus_dir) -> dict:
    """provision id -> its parent statute id, so a provision quote can be
    checked against the whole statute as the e-Library publishes it."""
    path = pathlib.Path(corpus_dir) / "provisions.json"
    if not path.exists():
        return {}
    return {
        p["id"]: p["doc_id"] for p in json.loads(path.read_text(encoding="utf-8"))
    }


def validate_item(
    item: dict,
    index: dict,
    cutoff: datetime.date,
    superseded: dict | None = None,
    elibrary: dict | None = None,
    parents: dict | None = None,
    source_urls: dict | None = None,
) -> None:
    superseded = superseded or {}
    elibrary = elibrary or {}
    parents = parents or {}
    source_urls = source_urls or {}
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

        # A fabricated link is as damaging as a fabricated quote: the student
        # clicks it and lands somewhere that does not say what we claimed.
        expected_url = source_urls.get(doc_id)
        if expected_url and authority.get("source_url") != expected_url:
            fail(
                f"source_url for {doc_id} does not match the corpus document. "
                f"Expected {expected_url!r}, got {authority.get('source_url')!r}"
            )

        if is_case(doc_id):
            context = str(authority.get("context", "")).strip()
            if len(context) < MIN_CONTEXT_LENGTH:
                fail(
                    f"case {doc_id} is cited without usable context. Give the parties, "
                    f"what was decided and why — a docket number alone teaches nothing."
                )

        quote = _normalise(str(authority.get("quote", "")))
        if len(quote) < MIN_QUOTE_LENGTH:
            fail(f"quote for {doc_id} is too short to prove grounding: {quote!r}")

        # PRIMARY SOURCE: the Supreme Court e-Library. The quote must appear
        # verbatim in the Court's own text. Fail closed — if the Court's copy
        # cannot be checked, the item does not ship.
        if elibrary:
            parent = parents.get(doc_id, doc_id)
            source = elibrary.get(parent)
            if source is None:
                fail(
                    f"no e-Library copy of {parent} is available, so the quote for "
                    f"{doc_id} cannot be checked against the Court's own text"
                )
            if quote not in _normalise(source["text"]):
                fail(
                    f"quote for {doc_id} does not appear in the e-Library text of "
                    f"{parent}: {quote[:60]!r}"
                )

        if elibrary:
            # SECONDARY SOURCE: lawphil, held in the corpus. A cross-check, not
            # a second authority. Spelling and punctuation drift between the two
            # transcriptions carries no legal weight; a changed qualifier or a
            # different provision does. Only the latter stops the item.
            drift = _drift_from(quote, entry["text"])
            if drift >= SIGNIFICANT:
                fail(
                    f"quote for {doc_id} diverges significantly from the secondary "
                    f"source (lawphil): {drift:.0%} different. Check whether the two "
                    f"texts state the same rule before shipping this."
                )
        elif quote not in _normalise(entry["text"]):
            # No primary source loaded, so the corpus IS the source of record
            # and exactness must hold against it. Never let a quote through
            # unchecked just because the e-Library copy is missing.
            fail(
                f"quote for {doc_id} was not found verbatim in the corpus: "
                f"{quote[:60]!r}"
            )


def is_case(doc_id: str) -> bool:
    return str(doc_id).startswith(CASE_PREFIXES)


def role_of(authority: dict) -> str:
    return authority.get("role", DEFAULT_ROLE)


def validate_bank(items, index, cutoff, superseded=None, elibrary=None, parents=None, source_urls=None):
    """Return (valid_items, error_messages). Bad items are dropped, not fixed."""
    valid = []
    errors = []

    counts = collections.Counter(i.get("id") for i in items)
    for item_id, n in counts.items():
        if n > 1:
            errors.append(f"{item_id}: duplicate id appears {n} times")

    for item in items:
        try:
            validate_item(item, index, cutoff, superseded, elibrary, parents, source_urls)
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        valid.append(item)

    return valid, errors
