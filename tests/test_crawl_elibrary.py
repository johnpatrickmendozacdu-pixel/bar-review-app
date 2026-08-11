import datetime
import pathlib

import pytest

from ingest.crawl_elibrary import (
    crawl_decision_urls,
    month_url,
    months_until,
    parse_month_index,
)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "elibrary_month.html"
CUTOFF = datetime.date(2025, 6, 30)


class StubFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


def test_month_url_uses_the_three_letter_month():
    assert month_url(2025, 6) == (
        "https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/Jun/2025/1"
    )


def test_month_url_handles_every_month():
    assert month_url(2024, 1).endswith("/Jan/2024/1")
    assert month_url(2024, 12).endswith("/Dec/2024/1")


def test_parse_month_index_finds_decision_urls():
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    urls = parse_month_index(html)
    assert urls, "the June 2025 fixture contains at least one decision"
    assert all("showdocs" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)


def test_parse_month_index_reads_single_quoted_hrefs():
    """The real e-Library markup single-quotes its decision hrefs."""
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    assert (
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/70158"
        in parse_month_index(html)
    )


def test_parse_month_index_deduplicates():
    html = (
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/1">a</a>'
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/1">a</a>'
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/2">b</a>'
    )
    assert len(parse_month_index(html)) == 2


def test_parse_month_index_ignores_non_decision_links():
    html = '<a href="/thebookshelf/2">Republic Acts</a><a href="/about">About</a>'
    assert parse_month_index(html) == []


def test_months_until_never_returns_a_month_after_the_cutoff():
    months = months_until(CUTOFF, years_back=2)
    assert (2025, 7) not in months
    assert (2026, 1) not in months
    assert (2025, 6) in months


def test_months_until_is_newest_first():
    months = months_until(CUTOFF, years_back=2)
    assert months[0] == (2025, 6)
    assert months[1] == (2025, 5)


def test_months_until_spans_the_requested_years():
    months = months_until(CUTOFF, years_back=2)
    assert len(months) == 24
    assert months[-1] == (2023, 7)


def test_crawl_collects_urls_across_months():
    pages = {
        month_url(2025, 6): '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/1">x</a>',
        month_url(2025, 5): '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/2">y</a>',
    }
    fetcher = StubFetcher(pages)
    urls = crawl_decision_urls(fetcher, CUTOFF, years_back=1, limit=10)
    assert len(urls) == 2


def test_crawl_stops_at_the_limit():
    pages = {
        month_url(2025, 6): "".join(
            f'<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{i}">x</a>'
            for i in range(10)
        )
    }
    urls = crawl_decision_urls(StubFetcher(pages), CUTOFF, years_back=1, limit=3)
    assert len(urls) == 3


def test_a_missing_month_page_does_not_abort_the_crawl():
    pages = {
        month_url(2025, 5): '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/2">y</a>'
    }
    urls = crawl_decision_urls(StubFetcher(pages), CUTOFF, years_back=1, limit=10)
    assert len(urls) == 1, "June 404s; May must still be collected"


def test_months_can_be_walked_oldest_first():
    """Older months hold far more decisions (Mar 1998: 86, Jun 2005: 166) than
    recent ones, so crawling from the dense end reaches a target count in a
    fraction of the requests."""
    months = months_until(CUTOFF, years_back=3, oldest_first=True)
    assert months[0] == (2022, 7)
    assert months[-1] == (2025, 6)


def test_oldest_first_still_excludes_post_cutoff_months():
    months = months_until(CUTOFF, years_back=3, oldest_first=True)
    assert (2025, 7) not in months
