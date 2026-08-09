"""Save a real page to tests/fixtures/ so parsers can be tested offline.

Usage: python -m tools.capture_fixture <url> <fixture-name>
"""

import pathlib
import sys

from ingest.fetch import Fetcher

FIXTURES = pathlib.Path(__file__).parent.parent / "tests" / "fixtures"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    url, name = sys.argv[1], sys.argv[2]
    FIXTURES.mkdir(parents=True, exist_ok=True)
    html = Fetcher(pathlib.Path(".cache")).get(url)
    out = FIXTURES / f"{name}.html"
    out.write_text(html, encoding="utf-8")
    print(f"Saved {len(html)} bytes to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
