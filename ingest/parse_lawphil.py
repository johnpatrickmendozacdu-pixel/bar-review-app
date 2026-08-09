"""lawphil.net HTML -> Document. Pure function, no I/O."""

import datetime
import re

from bs4 import BeautifulSoup

from ingest import config
from ingest.schema import Document

_DATE = r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})"

# lawphil puts the enactment date at the END, after "Approved:". The body often
# cites OLDER laws by date first, so scanning for the first date is wrong.
_APPROVED = re.compile(r"Approved\s*:?\s*" + _DATE)
_ANY_DATE = re.compile(_DATE)

_RA = re.compile(r"Republic Act No\.?\s*(\d+)", re.IGNORECASE)
_ACT = re.compile(r"\bAct No\.?\s*(\d+)", re.IGNORECASE)

# "AN ACT TO ORDAIN AND INSTITUTE THE CIVIL CODE OF THE PHILIPPINES"
_LONG_TITLE = re.compile(r"\bAN ACT\b[^.]{10,400}")


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
    # Fall back to the LAST date in the document, not the first — enactment
    # dates trail the body text.
    for match in reversed(list(_ANY_DATE.finditer(text))):
        date = _parse_date(match.groups())
        if date:
            return date
    return None


def parse_statute(html: str, source_url: str) -> Document:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    if not text.strip():
        raise ValueError(f"no text parsed from {source_url}; markup may have changed")

    flat = " ".join(text.split())

    ra = _RA.search(flat)
    act = _ACT.search(flat)
    if ra:
        citation = f"Republic Act No. {ra.group(1)}"
        doc_id = f"ra-{ra.group(1)}"
    elif act:
        citation = f"Act No. {act.group(1)}"
        doc_id = f"act-{act.group(1)}"
    else:
        raise ValueError(f"no Republic Act or Act number found in {source_url}")

    long_title = _LONG_TITLE.search(flat)
    if long_title:
        title = long_title.group(0).strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    else:
        title = citation

    date = _extract_date(flat)
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
