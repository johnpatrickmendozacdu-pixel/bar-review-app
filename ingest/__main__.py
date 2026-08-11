"""Ingest orchestrator. Run with: python -m ingest"""

import datetime
import json
import pathlib
import sys

from ingest import config
from ingest.crawl_elibrary import crawl_decision_urls, month_url, parse_month_index
from ingest.crawl_state import load_state, next_months, save_state
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
            parser = PARSERS[source]
            doc = (
                parser(html, seed["url"], meta=seed)
                if source == "lawphil"
                else parser(html, seed["url"])
            )
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


STATE_PATH = pathlib.Path("corpus/crawl_state.json")


def ingest_slice(fetcher, cutoff, years_back, months_per_run, per_month):
    """Crawl the next unvisited months, capped per month so coverage spreads.

    A flat cap consumed its whole budget on consecutive 1997 months. Capping
    per month instead spreads the same effort across years.
    """
    done = load_state(STATE_PATH)
    documents = []

    for year, month in next_months(done, cutoff, years_back, months_per_run):
        try:
            index_html = fetcher.get(month_url(year, month))
        except Exception as exc:
            print(f"SKIP index {year}-{month:02d}: {exc}", file=sys.stderr)
            continue

        taken = 0
        for url in parse_month_index(index_html):
            if taken >= per_month:
                break
            try:
                doc = parse_case(fetcher.get(url), url)
            except Exception as exc:
                print(f"FAILED {url}: {exc}", file=sys.stderr)
                continue
            if doc.promulgation_date > cutoff:
                continue
            doc.subject = tag_subject(doc.text)
            documents.append(doc)
            taken += 1

        done.add(f"{year}-{month:02d}")
        print(f"{year}-{month:02d}: {taken} cases", file=sys.stderr)

    save_state(STATE_PATH, done)
    return documents


def ingest_cases(
    fetcher, cutoff: datetime.date, years_back: int, limit: int, oldest_first: bool = False
) -> list:
    """Crawl, parse, date-fence and subject-tag e-Library decisions.

    A decision after the cut-off is dropped rather than stored: the 2026 Bar
    cannot test it, so it must never reach an answer key.
    """
    documents = []
    for url in crawl_decision_urls(fetcher, cutoff, years_back, limit, oldest_first):
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


def run_cases(
    fetcher, out_dir: pathlib.Path, limit: int, years_back: int = 3, oldest_first: bool = False
) -> dict:
    """Statutes from seeds plus crawled cases, emitted as one corpus."""
    cases = ingest_cases(
        fetcher, config.COVERAGE_DATE, years_back=years_back, limit=limit,
        oldest_first=oldest_first,
    )
    print(f"Ingested {len(cases)} cases within the cut-off.", file=sys.stderr)

    statutes = []
    for seed in load_seeds(SEEDS_PATH):
        if seed["source"] != "lawphil":
            continue
        try:
            doc = parse_statute(fetcher.get(seed["url"]), seed["url"], meta=seed)
            doc.subject = seed.get("subject", "")
            doc.short_title = seed.get("short", "")
            statutes.append(doc)
        except Exception as exc:
            print(f"FAILED {seed['url']}: {exc}", file=sys.stderr)

    # merge=True: the corpus is downloaded once and accumulates across runs.
    manifest = emit(statutes + cases, out_dir, merge=True)
    provisions = [p for doc in statutes for p in split_provisions(doc)]
    pathlib.Path(out_dir, "provisions.json").write_text(
        json.dumps(provisions, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    manifest["provisions"] = len(provisions)
    return manifest


def main() -> int:
    fetcher = Fetcher(pathlib.Path(".cache"))

    if "--cases" in sys.argv:
        limit, years_back = 200, 3
        months_per_run, per_month = 0, 12
        for arg in sys.argv:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
            if arg.startswith("--years="):
                years_back = int(arg.split("=", 1)[1])
            if arg.startswith("--months="):
                months_per_run = int(arg.split("=", 1)[1])
            if arg.startswith("--per-month="):
                per_month = int(arg.split("=", 1)[1])
        if months_per_run:
            cases = ingest_slice(
                fetcher, config.COVERAGE_DATE, years_back, months_per_run, per_month
            )
            statutes = []
            for seed in load_seeds(SEEDS_PATH):
                if seed["source"] != "lawphil":
                    continue
                try:
                    doc = parse_statute(fetcher.get(seed["url"]), seed["url"], meta=seed)
                    doc.subject = seed.get("subject", "")
                    doc.short_title = seed.get("short", "")
                    statutes.append(doc)
                except Exception as exc:
                    print(f"FAILED {seed['url']}: {exc}", file=sys.stderr)
            manifest = emit(statutes + cases, CORPUS_DIR, merge=True)
            provisions = [p for doc in statutes for p in split_provisions(doc)]
            pathlib.Path(CORPUS_DIR, "provisions.json").write_text(
                json.dumps(provisions, indent=1, ensure_ascii=False), encoding="utf-8"
            )
            manifest["provisions"] = len(provisions)
            print(json.dumps(manifest, indent=1))
            return 0

        oldest_first = "--oldest-first" in sys.argv
        print(
            json.dumps(
                run_cases(fetcher, CORPUS_DIR, limit, years_back, oldest_first), indent=1
            )
        )
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
