import datetime
import json

from ingest.crawl_state import load_state, next_months, save_state

CUTOFF = datetime.date(2025, 6, 30)


def test_recent_months_come_first():
    """The Bar tests recent jurisprudence most heavily."""
    months = next_months(set(), CUTOFF, years_back=30, slice_size=3)
    assert months[0] == (2025, 6)
    assert months[1] == (2025, 5)


def test_months_already_done_are_skipped():
    months = next_months({"2025-06", "2025-05"}, CUTOFF, years_back=30, slice_size=2)
    assert (2025, 6) not in months
    assert months[0] == (2025, 4)


def test_a_slice_is_bounded():
    assert len(next_months(set(), CUTOFF, years_back=30, slice_size=7)) == 7


def test_nothing_after_the_cutoff_is_ever_crawled():
    months = next_months(set(), CUTOFF, years_back=30, slice_size=50)
    assert all((y, m) <= (2025, 6) for y, m in months)


def test_an_exhausted_range_returns_nothing():
    done = {f"{y}-{m:02d}" for y in range(1995, 2026) for m in range(1, 13)}
    assert next_months(done, CUTOFF, years_back=30, slice_size=5) == []


def test_state_round_trips(tmp_path):
    path = tmp_path / "crawl_state.json"
    save_state(path, {"2025-06", "2024-01"})
    assert load_state(path) == {"2025-06", "2024-01"}


def test_missing_state_file_is_an_empty_set(tmp_path):
    assert load_state(tmp_path / "absent.json") == set()
