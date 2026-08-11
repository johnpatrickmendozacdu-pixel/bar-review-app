import json

from ingest.shards import CASES_DIR, read_cases, write_cases


def case(doc_id, date):
    return {"id": doc_id, "type": "case", "promulgation_date": date, "text": "t", "source_url": "u"}


def test_cases_are_written_one_file_per_year(tmp_path):
    write_cases(tmp_path, [case("gr-1", "2025-03-04"), case("gr-2", "1997-07-01")])
    assert (tmp_path / CASES_DIR / "2025.json").exists()
    assert (tmp_path / CASES_DIR / "1997.json").exists()


def test_every_case_survives_a_round_trip(tmp_path):
    docs = [case(f"gr-{i}", f"{1997 + i % 20}-06-01") for i in range(60)]
    write_cases(tmp_path, docs)
    assert len(read_cases(tmp_path)) == 60


def test_only_touched_years_are_rewritten(tmp_path):
    write_cases(tmp_path, [case("gr-1", "1997-07-01")])
    before = (tmp_path / CASES_DIR / "1997.json").stat().st_mtime_ns
    write_cases(tmp_path, [case("gr-2", "2025-03-04")])
    after = (tmp_path / CASES_DIR / "1997.json").stat().st_mtime_ns
    assert before == after, "an untouched year's shard must not be rewritten"


def test_reading_an_empty_corpus_gives_nothing(tmp_path):
    assert read_cases(tmp_path) == []


def test_a_legacy_single_file_is_still_read(tmp_path):
    """So the migration can read what is already stored."""
    (tmp_path / "case.json").write_text(json.dumps([case("gr-9", "2001-01-01")]))
    assert len(read_cases(tmp_path)) == 1


def test_shards_and_legacy_file_are_merged_without_duplicates(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps([case("gr-1", "1997-07-01")]))
    write_cases(tmp_path, [case("gr-1", "1997-07-01"), case("gr-2", "1997-07-02")])
    assert len({c["id"] for c in read_cases(tmp_path)}) == 2
