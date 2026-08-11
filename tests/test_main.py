import pathlib

import pytest

from ingest.__main__ import load_seeds, run


class StubFetcher:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


STATUTE_HTML = (
    "<html><title>R.A. 386</title><body>"
    "<p>REPUBLIC ACT NO. 386 AN ACT TO ORDAIN AND INSTITUTE THE CIVIL CODE "
    "OF THE PHILIPPINES</p><p>" + ("Article text. " * 200) + "</p>"
    "<p>Approved: June 18, 1949.</p></body></html>"
)

CASE_HTML = (
    "<html><title>G.R. No. 111111 - ALPHA VS. BETA D E C I S I O N</title><body>"
    "<p>[ G.R. No. 111111, March 3, 2020 ]</p><p>" + ("Ruling text. " * 200) + "</p>"
    "</body></html>"
)


def test_load_seeds_reads_the_shipped_file():
    seeds = load_seeds(pathlib.Path("ingest/seeds.json"))
    assert len(seeds) >= 1
    assert {"url", "source", "subject"} <= set(seeds[0])


def test_every_shipped_seed_uses_a_known_source():
    seeds = load_seeds(pathlib.Path("ingest/seeds.json"))
    assert {s["source"] for s in seeds} <= {"lawphil", "elibrary"}


def test_run_writes_a_corpus(tmp_path):
    seeds = [{"url": "https://lawphil.net/a", "source": "lawphil", "subject": "civil"}]
    fetcher = StubFetcher({"https://lawphil.net/a": STATUTE_HTML})
    manifest = run(seeds, fetcher, tmp_path)
    assert manifest["total"] == 1
    assert (tmp_path / "statute.json").exists()


def test_run_handles_both_sources(tmp_path):
    seeds = [
        {"url": "https://lawphil.net/a", "source": "lawphil", "subject": "civil"},
        {"url": "https://elibrary.judiciary.gov.ph/b", "source": "elibrary", "subject": "civil"},
    ]
    fetcher = StubFetcher(
        {"https://lawphil.net/a": STATUTE_HTML, "https://elibrary.judiciary.gov.ph/b": CASE_HTML}
    )
    manifest = run(seeds, fetcher, tmp_path)
    assert manifest["counts"] == {"statute": 1, "case": 1}


def test_subject_is_recorded_on_the_document(tmp_path):
    seeds = [{"url": "https://lawphil.net/a", "source": "lawphil", "subject": "civil"}]
    fetcher = StubFetcher({"https://lawphil.net/a": STATUTE_HTML})
    run(seeds, fetcher, tmp_path)
    import json

    data = json.loads((tmp_path / "statute.json").read_text())
    assert data[0]["subject"] == "civil"


def test_one_dead_url_does_not_lose_the_others(tmp_path):
    seeds = [
        {"url": "https://lawphil.net/a", "source": "lawphil", "subject": "civil"},
        {"url": "https://lawphil.net/dead", "source": "lawphil", "subject": "civil"},
    ]
    fetcher = StubFetcher({"https://lawphil.net/a": STATUTE_HTML})
    manifest = run(seeds, fetcher, tmp_path)
    assert manifest["total"] == 1
    assert manifest["failures"] == ["https://lawphil.net/dead"]


def test_all_seeds_failing_raises_rather_than_writing_nothing(tmp_path):
    seeds = [{"url": "https://lawphil.net/dead", "source": "lawphil", "subject": "civil"}]
    with pytest.raises(Exception):
        run(seeds, StubFetcher({}), tmp_path)


def test_unknown_source_is_rejected(tmp_path):
    seeds = [{"url": "https://x/a", "source": "wikipedia", "subject": "civil"}]
    with pytest.raises(ValueError, match="wikipedia"):
        run(seeds, StubFetcher({"https://x/a": STATUTE_HTML}), tmp_path)


import datetime

from ingest.__main__ import ingest_cases

CUTOFF_DATE = datetime.date(2025, 6, 30)


def case_html(gr, month, year, body="The accused was charged with estafa under the Revised Penal Code. "):
    return (
        f"<html><title>G.R. No. {gr} - ALPHA VS. BETA D E C I S I O N</title><body>"
        f"<p>[ G.R. No. {gr}, {month} 3, {year} ]</p><p>{body * 60}</p></body></html>"
    )


class CrawlStub:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


def test_ingest_cases_drops_anything_after_the_cutoff():
    from ingest.crawl_elibrary import month_url

    index = '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/9">x</a>'
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/9": case_html(
            "999", "August", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert docs == [], "an August 2025 decision is past the June 2025 cut-off"


def test_ingest_cases_keeps_documents_within_the_fence():
    from ingest.crawl_elibrary import month_url

    index = '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/8">x</a>'
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/8": case_html(
            "888", "June", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert len(docs) == 1
    assert docs[0].citation == "G.R. No. 888"


def test_ingest_cases_tags_the_subject():
    from ingest.crawl_elibrary import month_url

    index = '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/7">x</a>'
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/7": case_html(
            "777", "June", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert docs[0].subject == "criminal"


def test_an_unparseable_case_does_not_abort_the_run():
    from ingest.crawl_elibrary import month_url

    index = (
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/6">a</a>'
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/5">b</a>'
    )
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/6": "<html><body>no docket here</body></html>",
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/5": case_html(
            "555", "June", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert len(docs) == 1
