"""Case storage, sharded by year.

A scheduled crawl commits every two hours. Holding every decision in one file
means each commit rewrites the whole thing — tens of megabytes of churn per
run, forever. Sharding by promulgation year means a run that touches 2025 and
2024 rewrites two small files and leaves the rest untouched.
"""

import collections
import json
import pathlib

CASES_DIR = "cases"
LEGACY = "case.json"


def read_cases(corpus_dir) -> list:
    """Every stored case, from shards and from the pre-shard file if present."""
    corpus_dir = pathlib.Path(corpus_dir)
    by_id = {}

    legacy = corpus_dir / LEGACY
    if legacy.exists():
        for doc in json.loads(legacy.read_text(encoding="utf-8")):
            by_id[doc["id"]] = doc

    shard_dir = corpus_dir / CASES_DIR
    if shard_dir.exists():
        for path in sorted(shard_dir.glob("*.json")):
            for doc in json.loads(path.read_text(encoding="utf-8")):
                by_id[doc["id"]] = doc

    return list(by_id.values())


def write_cases(corpus_dir, documents: list) -> None:
    """Write only the shards the given documents belong to."""
    shard_dir = pathlib.Path(corpus_dir) / CASES_DIR
    shard_dir.mkdir(parents=True, exist_ok=True)

    by_year = collections.defaultdict(list)
    for doc in documents:
        by_year[doc["promulgation_date"][:4]].append(doc)

    for year, docs in by_year.items():
        path = shard_dir / f"{year}.json"
        existing = {}
        if path.exists():
            for doc in json.loads(path.read_text(encoding="utf-8")):
                existing[doc["id"]] = doc
        for doc in docs:
            existing[doc["id"]] = doc
        path.write_text(
            json.dumps(sorted(existing.values(), key=lambda d: d["id"]), indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
