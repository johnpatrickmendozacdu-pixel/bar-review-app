"""Which months have already been crawled.

The corpus is downloaded once and accumulates. Each scheduled run takes a
slice of months not yet visited, so runs continue where the last one stopped
instead of re-fetching the same period forever — which is exactly how the
first attempt ended up with 259 cases all from one quarter of 1997.

Recent months come first: the Bar tests current jurisprudence most heavily,
and older landmarks are reached as the schedule works backwards.
"""

import json
import pathlib


def load_state(path) -> set:
    path = pathlib.Path(path)
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("done", []))


def save_state(path, done: set) -> None:
    pathlib.Path(path).write_text(
        json.dumps({"done": sorted(done)}, indent=1), encoding="utf-8"
    )


def next_months(done: set, cutoff, years_back: int, slice_size: int) -> list:
    """The next months to crawl, newest first, skipping those already done."""
    months = []
    year, month = cutoff.year, cutoff.month
    for _ in range(years_back * 12):
        if len(months) >= slice_size:
            break
        if f"{year}-{month:02d}" not in done:
            months.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return months
