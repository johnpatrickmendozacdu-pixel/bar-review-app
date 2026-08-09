"""Documents -> JSON shards + manifest, refusing to commit a broken corpus."""

import collections
import datetime
import json
import pathlib

from ingest import config
from ingest.schema import Document


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


def emit(documents: list[Document], out_dir: pathlib.Path) -> dict:
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

    previous = _load_previous_total(out_dir)
    if previous and len(documents) < previous * config.SHRINK_THRESHOLD:
        raise ShrinkError(
            f"corpus shrank from {previous} to {len(documents)} documents "
            f"(threshold {config.SHRINK_THRESHOLD:.0%}). "
            "This is a broken scrape until proven otherwise. Nothing written."
        )

    by_type = collections.defaultdict(list)
    for doc in documents:
        by_type[doc.type].append(doc.to_dict())

    for doc_type, docs in by_type.items():
        (out_dir / f"{doc_type}.json").write_text(
            json.dumps(docs, indent=1, ensure_ascii=False), encoding="utf-8"
        )

    manifest = {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "coverage_date": config.COVERAGE_DATE.isoformat(),
        "counts": {t: len(d) for t, d in by_type.items()},
        "total": len(documents),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8"
    )
    return manifest
