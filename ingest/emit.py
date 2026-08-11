"""Documents -> JSON shards + manifest, refusing to commit a broken corpus."""

import collections
import datetime
import json
import pathlib

from ingest import config
from ingest.schema import Document
from ingest.shards import read_cases, write_cases


class ShrinkError(RuntimeError):
    """The new corpus is materially smaller than the last good one."""


def _load_previous_total(out_dir: pathlib.Path) -> int:
    manifest = out_dir / "manifest.json"
    if not manifest.exists():
        return 0
    try:
        return json.loads(manifest.read_text()).get("total", 0)
    except json.JSONDecodeError:
        return 0


def _load_existing(out_dir: pathlib.Path) -> dict:
    """Everything already downloaded, keyed by id."""
    stored = {}
    path = out_dir / "statute.json"
    if path.exists():
        for doc in json.loads(path.read_text(encoding="utf-8")):
            stored[doc["id"]] = doc
    for doc in read_cases(out_dir):
        stored[doc["id"]] = doc
    return stored


def emit(documents: list[Document], out_dir: pathlib.Path, merge: bool = False) -> dict:
    """Write the corpus.

    With `merge`, this run's documents are added to what is already stored
    rather than replacing it, so the corpus is fetched once and accumulates
    across scheduled slices. A run that returns two documents can then never
    discard the two hundred already downloaded.
    """
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not documents:
        raise ShrinkError("refusing to write an empty corpus")

    # Validate everything BEFORE writing anything, so one bad document can
    # never replace a good shard.
    for doc in documents:
        doc.validate()

    ids = [d.id for d in documents]
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dupes:
        raise ValueError(f"duplicate document ids: {sorted(dupes)[:5]}")

    incoming = len(_load_existing(out_dir) | {d.id: d for d in documents}) if merge else len(documents)
    previous = _load_previous_total(out_dir)
    if previous and incoming < previous * config.SHRINK_THRESHOLD:
        raise ShrinkError(
            f"corpus shrank from {previous} to {incoming} documents "
            f"(threshold {config.SHRINK_THRESHOLD:.0%}). "
            "This is a broken scrape until proven otherwise. Nothing written."
        )

    combined = _load_existing(out_dir) if merge else {}
    for doc in documents:
        combined[doc.id] = doc.to_dict()

    by_type = collections.defaultdict(list)
    for doc in combined.values():
        by_type[doc["type"]].append(doc)

    for doc_type, docs in by_type.items():
        if doc_type == "case":
            # Sharded by year so a two-hourly commit rewrites only what changed.
            write_cases(out_dir, docs)
            continue
        (out_dir / f"{doc_type}.json").write_text(
            json.dumps(docs, indent=1, ensure_ascii=False), encoding="utf-8"
        )

    total = sum(len(v) for v in by_type.values())
    manifest = {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "coverage_date": config.COVERAGE_DATE.isoformat(),
        "counts": {t: len(d) for t, d in by_type.items()},
        "total": total,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8"
    )
    return manifest
