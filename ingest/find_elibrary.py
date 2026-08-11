"""Locate a statute's own copy in the Supreme Court e-Library.

The e-Library indexes statutes the same way it indexes decisions: by month,
with a shelf id in the last path segment. Republic Acts live on shelf 2, Acts
on 28, Presidential Decrees on 26. So a statute can be found from its number
plus its enactment month.

This exists so every quotation in the question bank can be checked against the
Court's own text, not only against lawphil. A transcription difference between
the two is a signal to stop, not a rounding error.
"""

import re
import sys

from bs4 import BeautifulSoup

from ingest.crawl_elibrary import MONTH_ABBR
from ingest.text import repair_mojibake

BASE = "https://elibrary.judiciary.gov.ph/thebookshelf"

# e-Library shelf ids by statute kind, keyed by our document-id prefix.
SHELVES = {
    "ra": 2,
    "act": 28,
    "pd": 26,
    "bp": 25,
    "ca": 29,
    "eo": 5,
}


def month_index_url(shelf: int, year: int, month: int) -> str:
    return f"{BASE}/docmonth/{MONTH_ABBR[month - 1]}/{year}/{shelf}"


def find_statute(fetcher, doc_id: str, year: int, month: int) -> str | None:
    """Return the e-Library URL for a statute, or None if it is not listed.

    `doc_id` is our own id, e.g. "ra-386" or "act-3815". Matching is on the
    statute NUMBER as a whole word, so RA 386 never matches RA 3861.
    """
    kind, _, number = doc_id.partition("-")
    shelf = SHELVES.get(kind)
    if shelf is None:
        return None

    try:
        html = fetcher.get(month_index_url(shelf, year, month))
    except Exception as exc:
        print(f"SKIP index {doc_id} {year}-{month:02d}: {exc}", file=sys.stderr)
        return None

    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"\bNo\.?\s*{re.escape(number)}\b", re.IGNORECASE)

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "showdocs" not in href:
            continue
        if pattern.search(anchor.get_text(" ", strip=True)):
            return href if href.startswith("http") else f"https://elibrary.judiciary.gov.ph{href}"
    return None


def extract_text(html: str) -> str:
    """Plain text of an e-Library statute page, site chrome removed."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    for chrome in ("Supreme Court E-Library", "Information At Your Fingertips"):
        text = text.replace(chrome, "")
    return " ".join(repair_mojibake(text).split())
