"""SC e-Library HTML -> Document. Pure function, no I/O."""

import datetime
import re

from bs4 import BeautifulSoup

from ingest import config
from ingest.schema import Document
from ingest.text import repair_mojibake

# The e-Library prints a canonical header line per decision:
#     [ G.R. No. 279692, June 11, 2025 ]
# Docket and promulgation date together. Far more reliable than scanning the
# body, which quotes other cases and their dates throughout.
_HEADER = re.compile(
    r"\[\s*(?P<docket>(?:G\.?\s*R\.?|A\.?\s*M\.?|A\.?\s*C\.?)[^,\]]*?)\s*,\s*"
    r"(?P<month>[A-Z][a-z]+)\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4})\s*\]",
    re.IGNORECASE,
)

_GR_NUMBER = re.compile(r"(\d+)")

# The e-Library's own site chrome, which appears in every page's text.
_CHROME = ("Supreme Court E-Library", "Information At Your Fingertips")


def _clean_docket(docket: str) -> str:
    """'G.R. No. 279692' from any of the spacing/punctuation variants."""
    flat = " ".join(docket.split())
    flat = re.sub(r"^G\.?\s*R\.?\s*", "G.R. ", flat, flags=re.IGNORECASE)
    flat = re.sub(r"^A\.?\s*M\.?\s*", "A.M. ", flat, flags=re.IGNORECASE)
    flat = re.sub(r"^A\.?\s*C\.?\s*", "A.C. ", flat, flags=re.IGNORECASE)
    flat = re.sub(r"\bNos?\.?\s*", "No. ", flat, flags=re.IGNORECASE)
    return " ".join(flat.split())


def _title_from(soup, fallback: str) -> str:
    """Party names. The <title> tag carries them but also the docket, the
    'D E C I S I O N' marker and the site name."""
    raw = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    if not raw:
        return fallback
    for marker in ("D E C I S I O N", "R E S O L U T I O N"):
        raw = raw.split(marker)[0]
    raw = raw.replace("- Supreme Court E-Library", "")
    # The e-Library's own titles contain malformed tags, e.g. "DOLORBR>" from a
    # broken <BR>. Strip the leaked fragment, keeping the word it collided with.
    raw = re.sub(r"\s*<?\s*[Bb][Rr]\s*>\s*", " ", raw)
    # Drop the leading "G.R. No. NNNN - " prefix; keep the party names.
    raw = re.sub(r"^\s*[A-Z]\.?\s*[A-Z]\.?\s*Nos?\.[^-]*-\s*", "", raw).strip()
    raw = " ".join(raw.split()).strip(" -,")
    if not raw:
        return fallback
    return raw[:300]


def parse_case(html: str, source_url: str) -> Document:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    text = repair_mojibake(text)
    if not text.strip():
        raise ValueError(f"no text parsed from {source_url}; markup may have changed")

    flat = " ".join(text.split())

    header = _HEADER.search(flat)
    if header:
        citation = _clean_docket(header.group("docket"))
        try:
            date = datetime.datetime.strptime(
                f"{header.group('month')} {header.group('day')} {header.group('year')}",
                "%B %d %Y",
            ).date()
        except ValueError as exc:
            raise ValueError(f"unparseable date in header of {source_url}") from exc
    else:
        # No canonical header. Require a docket at minimum, and refuse to guess
        # a date from the body — a wrong date silently breaks the cutoff fence.
        loose = re.search(r"G\.?\s*R\.?\s*Nos?\.?\s*\d+", flat, re.IGNORECASE)
        if not loose:
            raise ValueError(f"no G.R. number found in {source_url}")
        raise ValueError(
            f"found a docket but no promulgation date in {source_url}; "
            "refusing to guess — the cutoff fence depends on this date"
        )

    number = _GR_NUMBER.search(citation)
    if not number:
        raise ValueError(f"no numeric docket in {citation!r} from {source_url}")

    prefix = (
        "gr"
        if citation.upper().startswith("G.R.")
        else citation.split()[0].lower().replace(".", "")
    )

    # Use the WHOLE docket, not the first number in it. Administrative matters
    # are numbered "A.M. No. 93-2-1011-RTC" — the leading 93 is the year, so
    # taking the first number collapses every 1993 A.M. onto one id.
    docket = re.sub(r"^.*?Nos?\.\s*", "", citation, flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", "-", docket.lower()).strip("-")
    if not slug:
        slug = number.group(1)

    body = text
    for chrome in _CHROME:
        body = body.replace(chrome, "")

    return Document(
        id=f"{prefix}-{slug}",
        schema_version=config.SCHEMA_VERSION,
        type="case",
        title=_title_from(soup, citation),
        citation=citation,
        promulgation_date=date,
        source_url=source_url,
        text=body.strip(),
    )
