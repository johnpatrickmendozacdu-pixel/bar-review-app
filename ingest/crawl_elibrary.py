"""Enumerate e-Library decisions by month. No parsing of decisions here."""

import datetime
import re
import sys

BASE = "https://elibrary.judiciary.gov.ph/thebookshelf"

MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

# The real month index single-quotes its hrefs (see tests/fixtures/
# elibrary_month.html); the rest of the site double-quotes. Accept both.
_DECISION_HREF = re.compile(r"""href=["']([^"']*showdocs/\d+/\d+)["']""")


def month_url(year: int, month: int) -> str:
    return f"{BASE}/docmonth/{MONTH_ABBR[month - 1]}/{year}/1"


def parse_month_index(html: str) -> list[str]:
    """Decision URLs on a month index page, deduped, order preserved."""
    urls = []
    seen = set()
    for href in _DECISION_HREF.findall(html):
        url = (
            href
            if href.startswith("http")
            else f"https://elibrary.judiciary.gov.ph{href}"
        )
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def months_until(cutoff: datetime.date, years_back: int) -> list[tuple[int, int]]:
    """(year, month) pairs ending at the cut-off month, newest first."""
    months = []
    year, month = cutoff.year, cutoff.month
    for _ in range(years_back * 12):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months


def crawl_decision_urls(
    fetcher, cutoff: datetime.date, years_back: int, limit: int
) -> list[str]:
    """Decision URLs across months. One dead month must not abort the crawl."""
    urls = []
    for year, month in months_until(cutoff, years_back):
        if len(urls) >= limit:
            break
        try:
            html = fetcher.get(month_url(year, month))
        except Exception as exc:
            print(f"SKIP {year}-{month:02d}: {exc}", file=sys.stderr)
            continue
        for url in parse_month_index(html):
            if len(urls) >= limit:
                break
            urls.append(url)
    return urls
