"""Validate the shipped question bank. Run with: python -m bank"""

import datetime
import json
import pathlib
import sys

from bank.validate import build_index, validate_bank

CUTOFF = datetime.date(2025, 6, 30)


def main() -> int:
    items = json.loads(pathlib.Path("bank/questions.json").read_text(encoding="utf-8"))
    index = build_index(pathlib.Path("corpus"))
    valid, errors = validate_bank(items, index, CUTOFF)

    print(f"{len(valid)} valid, {len(errors)} rejected, {len(index)} corpus documents")
    for error in errors:
        print(f"  REJECTED {error}", file=sys.stderr)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
