"""Ingest orchestrator. Run with: python -m ingest"""

import datetime
import json
import pathlib
import sys

from ingest import config
from ingest.crawl_elibrary import crawl_decision_urls
from ingest.emit import emit
from ingest.fetch import Fetcher
from ingest.parse_elibrary import parse_case
from ingest.parse_lawphil import parse_statute
from ingest.split import split_provisions
from ingest.subjects import tag_subject

PARSERS = {"lawphil": parse_statute, "elibrary": parse_case}

CORPUS_DIR = pathlib.Path("corpus")
SEEDS_PATH = pathlib.Path("ingest/seeds.json")


def load_seeds(path: pathlib.Path) -> list[dict]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def run(seeds: list[dict], fetcher, out_dir: pathlib.Path) -> dict:
    documents = []
    failures = []

    for seed in seeds:
        source = seed["source"]
        if source not in PARSERS:
            raise ValueError(
                f"unknown source {source!r}; expected one of {sorted(PARSERS)}"
            )
        try:
            html = fetcher.get(seed["url"])
            doc = PARSERS[source](html, seed["url"])
            doc.subject = seed.get("subject", "")
            doc.short_title = seed.get("short", "")
            documents.append(doc)
        except Exception as exc:  # one bad URL must not cost us the rest
            print(f"FAILED {seed['url']}: {exc}", file=sys.stderr)
            failures.append(seed["url"])

    manifest = emit(documents, out_dir)

    provisions = [p for doc in documents for p in split_provisions(doc)]
    pathlib.Path(out_dir, "provisions.json").write_text(
        json.dumps(provisions, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    manifest["provisions"] = len(provisions)
    manifest["failures"] = failures
    return manifest


def ingest_cases(fetcher, cutoff: datetime.date, years_back: int, limit: int) -> list:
    """Crawl, parse, date-fence and subject-tag e-Library decisions.

    A decision after the cut-off is dropped rather than stored: the 2026 Bar
    cannot test it, so it must never reach an answer key.
    """
    documents = []
    for url in crawl_decision_urls(fetcher, cutoff, years_back, limit):
        try:
            doc = parse_case(fetcher.get(url), url)
        except Exception as exc:
            print(f"FAILED {url}: {exc}", file=sys.stderr)
            continue
        if doc.promulgation_date > cutoff:
            print(
                f"PAST CUTOFF {doc.citation} ({doc.promulgation_date})",
                file=sys.stderr,
            )
            continue
        doc.subject = tag_subject(doc.text)
        documents.append(doc)
    return documents


def run_cases(fetcher, out_dir: pathlib.Path, limit: int) -> dict:
    """Statutes from seeds plus crawled cases, emitted as one corpus."""
    cases = ingest_cases(fetcher, config.COVERAGE_DATE, years_back=3, limit=limit)
    print(f"Ingested {len(cases)} cases within the cut-off.", file=sys.stderr)

    statutes = []
    for seed in load_seeds(SEEDS_PATH):
        if seed["source"] != "lawphil":
            continue
        try:
            doc = parse_statute(fetcher.get(seed["url"]), seed["url"])
            doc.subject = seed.get("subject", "")
            doc.short_title = seed.get("short", "")
            statutes.append(doc)
        except Exception as exc:
            print(f"FAILED {seed['url']}: {exc}", file=sys.stderr)

    manifest = emit(statutes + cases, out_dir)
    provisions = [p for doc in statutes for p in split_provisions(doc)]
    pathlib.Path(out_dir, "provisions.json").write_text(
        json.dumps(provisions, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    manifest["provisions"] = len(provisions)
    return manifest


def main() -> int:
    fetcher = Fetcher(pathlib.Path(".cache"))

    if "--cases" in sys.argv:
        limit = 200
        for arg in sys.argv:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(run_cases(fetcher, CORPUS_DIR, limit), indent=1))
        return 0

    manifest = run(load_seeds(SEEDS_PATH), fetcher, CORPUS_DIR)
    print(json.dumps(manifest, indent=1))
    if manifest["failures"]:
        print(
            f"\n{len(manifest['failures'])} seed(s) failed. Corpus written from "
            "the rest.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
