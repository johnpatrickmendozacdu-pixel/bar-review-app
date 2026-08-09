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
