import datetime
import json

import pytest

from ingest.emit import ShrinkError, emit
from ingest.schema import Document


def make_docs(n, type_="statute"):
    return [
        Document(
            id=f"{type_}-{i}",
            schema_version=1,
            type=type_,
            title=f"Doc {i}",
            citation=f"Cite {i}",
            promulgation_date=datetime.date(2020, 1, 1),
            source_url="https://example.com/x",
            text="body text " * 20,
        )
        for i in range(n)
    ]


def test_writes_one_shard_per_type(tmp_path):
    emit(make_docs(3, "statute") + make_docs(2, "case"), tmp_path)
    assert (tmp_path / "statute.json").exists()
    assert (tmp_path / "case.json").exists()


def test_manifest_records_counts(tmp_path):
    manifest = emit(make_docs(3, "statute") + make_docs(2, "case"), tmp_path)
    assert manifest["counts"] == {"statute": 3, "case": 2}
    assert manifest["total"] == 5


def test_manifest_records_the_coverage_date(tmp_path):
    manifest = emit(make_docs(1), tmp_path)
    assert manifest["coverage_date"] == "2025-06-30"


def test_shard_contents_are_serialized_documents(tmp_path):
    emit(make_docs(1), tmp_path)
    data = json.loads((tmp_path / "statute.json").read_text())
    assert data[0]["id"] == "statute-0"
    assert data[0]["promulgation_date"] == "2020-01-01"


def test_invalid_document_is_rejected_before_writing(tmp_path):
    bad = make_docs(1)
    bad[0].text = ""
    with pytest.raises(ValueError, match="text"):
        emit(bad, tmp_path)
    assert not (tmp_path / "statute.json").exists()


def test_growth_is_allowed(tmp_path):
    emit(make_docs(10), tmp_path)
    manifest = emit(make_docs(20), tmp_path)
    assert manifest["total"] == 20


def test_material_shrink_raises_and_leaves_old_corpus_intact(tmp_path):
    emit(make_docs(100), tmp_path)
    with pytest.raises(ShrinkError, match="100"):
        emit(make_docs(10), tmp_path)
    data = json.loads((tmp_path / "statute.json").read_text())
    assert len(data) == 100, "the last good corpus must survive a failed run"


def test_trivial_shrink_within_threshold_is_allowed(tmp_path):
    emit(make_docs(100), tmp_path)
    manifest = emit(make_docs(97), tmp_path)
    assert manifest["total"] == 97


def test_empty_corpus_is_always_rejected(tmp_path):
    with pytest.raises(ShrinkError):
        emit([], tmp_path)


def test_duplicate_ids_are_rejected(tmp_path):
    docs = make_docs(2)
    docs[1].id = docs[0].id
    with pytest.raises(ValueError, match="duplicate"):
        emit(docs, tmp_path)


def test_emit_merges_with_what_is_already_stored(tmp_path):
    """The corpus is fetched once and accumulates. A later run that sees fewer
    documents must not discard the ones already downloaded."""
    emit(make_docs(5, "case"), tmp_path, merge=True)
    second = make_docs(2, "statute")
    manifest = emit(second, tmp_path, merge=True)
    assert manifest["total"] == 7, "existing cases must survive a statute-only run"


def test_merge_updates_a_document_that_changed(tmp_path):
    emit(make_docs(1), tmp_path, merge=True)
    updated = make_docs(1)
    updated[0].title = "Amended title"
    emit(updated, tmp_path, merge=True)
    data = json.loads((tmp_path / "statute.json").read_text())
    assert len(data) == 1
    assert data[0]["title"] == "Amended title"


def test_merge_makes_a_partial_run_safe(tmp_path):
    """A crawl slice of two documents must not trip the shrink guard when the
    corpus already holds a hundred."""
    emit(make_docs(100, "case"), tmp_path, merge=True)
    manifest = emit(make_docs(2, "statute"), tmp_path, merge=True)
    assert manifest["total"] == 102


def test_without_merge_the_old_replace_behaviour_still_applies(tmp_path):
    emit(make_docs(10), tmp_path)
    with pytest.raises(ShrinkError):
        emit(make_docs(2), tmp_path)
