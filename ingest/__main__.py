"""Ingest orchestrator. Run with: python -m ingest"""

import json
import pathlib
import sys

from ingest.emit import emit
from ingest.fetch import Fetcher
from ingest.parse_elibrary import parse_case
from ingest.parse_lawphil import parse_statute
from ingest.split import split_provisions

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


def main() -> int:
    fetcher = Fetcher(pathlib.Path(".cache"))
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
