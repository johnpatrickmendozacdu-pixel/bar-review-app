"""Fetch the Supreme Court's own copy of every statute cited by the bank.

The e-Library is the PRIMARY source: every quotation in a question must appear
verbatim in the Court's text. lawphil, held in the corpus, is a secondary
cross-reference.

Run after adding statutes to the corpus or citing a new one:

    python -m tools.refresh_elibrary
"""

import json
import pathlib
import sys

from ingest.fetch import Fetcher
from ingest.find_elibrary import extract_text, find_statute

OUT = pathlib.Path("corpus/elibrary_statutes.json")

# The e-Library sometimes files a statute under a neighbouring month from its
# stated approval date — RA 6552 is dated August 1972 on lawphil but listed
# under September. Search either side before giving up.
NEARBY = (0, 1, -1, 2, -2)


def shift(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + month - 1) + delta
    return index // 12, index % 12 + 1


def main() -> int:
    statutes = {
        d["id"]: d["promulgation_date"]
        for d in json.loads(pathlib.Path("corpus/statute.json").read_text())
    }
    bank = json.loads(pathlib.Path("bank/questions.json").read_text())
    provisions = {
        p["id"]: p["doc_id"]
        for p in json.loads(pathlib.Path("corpus/provisions.json").read_text())
    }

    # Every parent statute the bank actually cites.
    wanted = set()
    for item in bank:
        for authority in item.get("authorities", []):
            doc_id = authority["doc_id"]
            wanted.add(provisions.get(doc_id, doc_id))

    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    fetcher = Fetcher(pathlib.Path(".cache"))
    missing = []

    for doc_id in sorted(wanted):
        if doc_id in existing:
            continue
        date = statutes.get(doc_id)
        if not date:
            missing.append(f"{doc_id} (not a statute in the corpus)")
            continue

        year, month = int(date[:4]), int(date[5:7])
        url = None
        for delta in NEARBY:
            y, m = shift(year, month, delta)
            url = find_statute(fetcher, doc_id, y, m)
            if url:
                break

        if not url:
            missing.append(f"{doc_id} (no e-Library listing near {date})")
            continue

        existing[doc_id] = {"url": url, "text": extract_text(fetcher.get(url))}
        print(f"{doc_id}: {len(existing[doc_id]['text']):>8} chars  {url}")

    OUT.write_text(json.dumps(existing, indent=1, ensure_ascii=False))
    print(f"\n{len(existing)} statutes verified against the e-Library")

    if missing:
        print("\nNOT FOUND — questions citing these will fail closed:", file=sys.stderr)
        for entry in missing:
            print(f"  {entry}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
