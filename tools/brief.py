"""Brief a decision for authoring: find where the Court speaks in its own voice.

Reading a thirty-page decision to locate the two sentences that state its
holding is the slow part of writing a question. Worse, decisions quote parties,
lower courts and agencies constantly — quoting one of those as if it were the
Court's holding produces an item that passes every mechanical check and is
still wrong. That happened once already, with a Ministry of Justice opinion
quoted inside Director of Lands v. Abistado.

This prints the disposition, the candidate holdings, and — critically — marks
which candidates sit inside quotation marks, meaning somebody else is talking.

Usage:
    python -m tools.brief gr-102858
    python -m tools.brief gr-102858 --search rescission
"""

import json
import pathlib
import re
import sys

# Phrases where the Court speaks for itself rather than reporting an argument.
COURT_VOICE = (
    "we hold",
    "we rule",
    "we find",
    "we agree",
    "we disagree",
    "the court holds",
    "the court rules",
    "this court has",
    "it is well-settled",
    "it is settled",
    "we are not persuaded",
    "the petition is",
    "we sustain",
    "we reverse",
    "we affirm",
)

OPEN_QUOTES = "“‘\""
CLOSE_QUOTES = "”’\""


def load_case(doc_id: str) -> dict | None:
    from ingest.shards import read_cases

    docs = list(read_cases("corpus"))
    path = pathlib.Path("corpus/statute.json")
    if path.exists():
        docs.extend(json.loads(path.read_text(encoding="utf-8")))
    for doc in docs:
        if doc["id"] == doc_id:
            return doc
    return None


def quoted_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges enclosed in quotation marks — i.e. not the Court."""
    spans = []
    start = None
    for i, char in enumerate(text):
        if start is None and char in OPEN_QUOTES:
            start = i
        elif start is not None and char in CLOSE_QUOTES and i > start:
            spans.append((start, i))
            start = None
    return spans


def inside_quotes(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position <= end for start, end in spans)


def sentences(text: str) -> list[tuple[int, str]]:
    out, position = [], 0
    for part in re.split(r"(?<=[.;])\s+", text):
        out.append((position, part.strip()))
        position += len(part) + 1
    return out


def brief(doc: dict, search: str | None = None) -> None:
    text = " ".join(doc["text"].split())
    spans = quoted_spans(text)

    print(f"{doc['citation']}  ({doc['promulgation_date']})")
    print(f"{doc['title'][:150]}")
    print(f"{doc['source_url']}")
    print(f"{len(text):,} characters, {len(spans)} quoted passages")

    ponente = re.search(r"([A-Z][A-Za-z.\- ]{2,40}),?\s+J\.:", text)
    if ponente:
        print(f"Ponente: {ponente.group(1).strip()}")

    disposition = re.search(r"WHEREFORE.{0,700}?SO ORDERED", text, re.DOTALL)
    if disposition:
        print("\n--- DISPOSITION ---")
        print(disposition.group(0)[:700])

    print("\n--- CANDIDATE HOLDINGS ---")
    print("[COURT] = the Court's own voice.  [QUOTED] = someone else — do not attribute.\n")

    found = 0
    for position, sentence in sentences(text):
        lowered = sentence.lower()
        if search and search.lower() not in lowered:
            continue
        if not search and not any(phrase in lowered for phrase in COURT_VOICE):
            continue
        if len(sentence) < 40:
            continue

        tag = "QUOTED" if inside_quotes(position, spans) else "COURT "
        print(f"[{tag}] {sentence[:400]}\n")
        found += 1
        if found >= 25:
            print("... truncated at 25 matches; narrow with --search")
            break

    if not found:
        print("(none — try --search with a doctrinal keyword)")

    print("--- AUTHORITY STUB (source_url is taken from the corpus, not typed) ---")
    print(
        json.dumps(
            {
                "doc_id": doc["id"],
                "citation": f"{doc['citation']} ({doc['promulgation_date']})",
                "role": "controlling",
                "quote": "<paste a [COURT] sentence verbatim>",
                "source_url": doc["source_url"],
            },
            indent=1,
        )
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    doc = load_case(sys.argv[1])
    if not doc:
        print(f"{sys.argv[1]} is not in the corpus", file=sys.stderr)
        return 1

    search = None
    if "--search" in sys.argv:
        search = sys.argv[sys.argv.index("--search") + 1]
    brief(doc, search)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
