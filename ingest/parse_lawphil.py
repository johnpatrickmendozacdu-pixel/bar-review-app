"""lawphil.net HTML -> Document. Pure function, no I/O."""

import datetime
import re

from bs4 import BeautifulSoup

from ingest import config
from ingest.schema import Document

_DATE = r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})"

# How much of the document counts as "the head" for identifying it.
HEAD_CHARS = 1200

# lawphil puts the enactment date at the END, after "Approved:". The body often
# cites OLDER laws by date first, so scanning for the first date is wrong.
_APPROVED = re.compile(r"Approved\s*:?\s*" + _DATE)
_ANY_DATE = re.compile(_DATE)

# Decrees and executive issuances close with "Done in the City of Manila, this
# 1st day of May, 1974" rather than an "Approved:" line.
_DONE_THIS_DAY = re.compile(
    r"this\s+(\d{1,2})(?:st|nd|rd|th)?\s+day\s+of\s+([A-Z][a-z]+),?\s+(\d{4})",
    re.IGNORECASE,
)

_RA = re.compile(r"Republic Act No\.?\s*(\d+)", re.IGNORECASE)
_ACT = re.compile(r"\bAct No\.?\s*(\d+)", re.IGNORECASE)

# Order matters: the more specific forms must be tried before the bare
# "Act No." pattern, which would otherwise swallow "Republic Act No." and
# "Commonwealth Act No.".
_NUMBERED = (
    ("ra", "Republic Act No.", re.compile(r"Republic Act No\.?\s*(\d+)", re.IGNORECASE)),
    ("pd", "Presidential Decree No.", re.compile(r"Presidential Decree No\.?\s*(\d+)", re.IGNORECASE)),
    ("bp", "Batas Pambansa Blg.", re.compile(r"Batas Pambansa (?:Blg|Bilang)\.?\s*(\d+)", re.IGNORECASE)),
    ("ca", "Commonwealth Act No.", re.compile(r"Commonwealth Act No\.?\s*(\d+)", re.IGNORECASE)),
    ("eo", "Executive Order No.", re.compile(r"Executive Order No\.?\s*(\d+)", re.IGNORECASE)),
    ("act", "Act No.", re.compile(r"\bAct No\.?\s*(\d+)", re.IGNORECASE)),
)

# "AN ACT TO ORDAIN AND INSTITUTE THE CIVIL CODE OF THE PHILIPPINES"
_LONG_TITLE = re.compile(r"\bAN ACT\b[^.]{10,400}")

# The long title runs straight into the statute's structure with no full stop
# between them, so cut at the first structural heading.
_STRUCTURE = re.compile(
    r"\b(PRELIMINARY\s+TITLE|BOOK\s+(?:ONE|TWO|I\b|II\b)|TITLE\s+(?:ONE|I\b)|"
    r"CHAPTER\s+(?:1|I|ONE)\b|ARTICLE\s+1\b|SECTION\s+1\b)",
    re.IGNORECASE,
)


def _parse_date(groups) -> datetime.date | None:
    try:
        return datetime.datetime.strptime(" ".join(groups), "%B %d %Y").date()
    except ValueError:
        return None


def _extract_date(text: str) -> datetime.date | None:
    approved = _APPROVED.search(text)
    if approved:
        date = _parse_date(approved.groups())
        if date:
            return date

    done = _DONE_THIS_DAY.search(text)
    if done:
        day, month, year = done.groups()
        date = _parse_date((month, day, year))
        if date:
            return date
    # Fall back to the LAST date in the document, not the first — enactment
    # dates trail the body text.
    for match in reversed(list(_ANY_DATE.finditer(text))):
        date = _parse_date(match.groups())
        if date:
            return date
    return None


def parse_statute(html: str, source_url: str, meta: dict | None = None) -> Document:
    """Parse a lawphil statute page.

    `meta` carries curated facts declared in the seed entry, and they WIN over
    inference. Whoever wrote the seed had the document in hand; the parser is
    guessing from text that cites other statutes constantly — the Labor Code
    cites RA 6727, the Rules of Court cite RA 6657, and inferring identity from
    the body picks those instead of the document itself.
    """
    meta = meta or {}
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    if not text.strip():
        raise ValueError(f"no text parsed from {source_url}; markup may have changed")

    flat = " ".join(text.split())

    # A declared seed wins: whoever wrote it had the document in hand. Inference
    # from body text is unreliable because statutes cite other statutes.
    if meta.get("id"):
        doc_id = meta["id"]
        citation = meta.get("citation") or doc_id
    else:
        citation = doc_id = None

    # Identity lives in the title and enacting clause, never deep in the body:
    # the Labor Code cites RA 6727, the Rules of Court cite RA 6657.
    if not doc_id:
        head = flat[:HEAD_CHARS]
        found = [
            (m.start(), slug, label, m.group(1))
            for slug, label, pattern in _NUMBERED
            if (m := pattern.search(head))
        ]
        if found:
            _, slug, label, number = min(found)
            citation = f"{label} {number}"
            doc_id = f"{slug}-{number}"

    if not doc_id:
        raise ValueError(
            f"no statute number found in {source_url} and no id declared in the seed"
        )

    long_title = _LONG_TITLE.search(flat)
    if long_title:
        title = _STRUCTURE.split(long_title.group(0))[0].strip(" ,;-")
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    else:
        title = citation

    date = (
        datetime.date.fromisoformat(meta["date"])
        if meta.get("date")
        else _extract_date(flat)
    )
    if date is None:
        raise ValueError(
            f"no enactment date parsed from {source_url}; "
            "the cutoff fence cannot work without it"
        )

    return Document(
        id=doc_id,
        schema_version=config.SCHEMA_VERSION,
        type="statute",
        title=title,
        citation=citation,
        promulgation_date=date,
        source_url=source_url,
        text=text,
    )
