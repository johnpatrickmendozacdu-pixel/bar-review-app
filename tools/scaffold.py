"""Scaffold question stubs with every mechanical field pre-filled and verified.

Authoring throughput was going into work that never needed a human: picking
provisions worth testing, hunting an exact quote, copying citations and URLs,
and re-running the validator to find out the quote was off by a word.

This does all of that. It selects provisions that actually state a rule, picks
a quote that is verified verbatim against BOTH the Supreme Court e-Library
(primary) and the corpus, and writes the citation and source_url straight from
the corpus so they can never be typed wrong. What is left is the part that
needs judgment: the facts, the reasoning, and the exceptions.

Usage:
    python -m tools.scaffold --subject labor --count 8
    python -m tools.scaffold --subject civil --count 5 --type doctrine
"""

import argparse
import json
import pathlib
import re
import sys

from bank.validate import (
    build_parents,
    elibrary_sources,
    load_cases,
    load_elibrary,
)

# Provisions that state a rule, not a definition or a repealing clause.
STATES_A_RULE = re.compile(
    r"\b(the following|requisites|elements|shall be (?:liable|punished|void)|"
    r"no .{0,30} unless|except|provided that|within .{0,20}(days|years)|"
    r"shall not|may be|is required)\b",
    re.IGNORECASE,
)

MIN_QUOTE, MAX_QUOTE = 60, 240


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.;:])\s+", " ".join(text.split()))]


def pick_quote(provision_text: str, primary_text: str) -> str | None:
    """The longest span present verbatim in BOTH sources.

    Verifying here means a scaffolded quote never fails the gate later, which
    is where most authoring time was being lost.
    """
    normalise = lambda t: " ".join(t.split())
    primary = normalise(primary_text)
    corpus = normalise(provision_text)

    best = None
    for sentence in sentences(provision_text):
        candidate = sentence.rstrip(".;:")
        if not (MIN_QUOTE <= len(candidate) <= MAX_QUOTE):
            continue
        if candidate in primary and candidate in corpus:
            if best is None or len(candidate) > len(best):
                best = candidate
    return best


def used_doc_ids(bank: list) -> set:
    return {a["doc_id"] for item in bank for a in item.get("authorities", [])}


def next_id(bank: list, subject: str) -> int:
    prefix = f"q-{subject}-"
    numbers = [
        int(item["id"][len(prefix) :])
        for item in bank
        if item["id"].startswith(prefix) and item["id"][len(prefix) :].isdigit()
    ]
    return max(numbers, default=0) + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--type", default="hypothetical")
    parser.add_argument("--out", default="bank/drafts.json")
    args = parser.parse_args()

    corpus = pathlib.Path("corpus")
    provisions = json.loads((corpus / "provisions.json").read_text())
    bank = json.loads(pathlib.Path("bank/questions.json").read_text())

    primary = elibrary_sources(
        load_elibrary(corpus / "elibrary_statutes.json"), load_cases(corpus)
    )
    parents = build_parents(corpus)
    already = used_doc_ids(bank)

    candidates = [
        p
        for p in provisions
        if p["subject"] == args.subject
        and p["id"] not in already
        and len(p["text"]) > 250
        and STATES_A_RULE.search(p["text"])
    ]
    # Longest first: a provision with more operative text supports a richer
    # question than a one-line rule.
    candidates.sort(key=lambda p: -len(p["text"]))

    drafts, skipped = [], 0
    for provision in candidates:
        if len(drafts) >= args.count:
            break
        parent = parents.get(provision["id"], provision["id"])
        source = primary.get(parent)
        if source is None:
            skipped += 1
            continue

        quote = pick_quote(provision["text"], source["text"])
        if not quote:
            skipped += 1
            continue

        drafts.append(
            {
                "id": f"q-{args.subject}-{next_id(bank, args.subject) + len(drafts):04d}",
                "schema_version": 2,
                "type": args.type,
                "subject": args.subject,
                "question": f"TODO facts and the call. Rule under test: {provision['citation']}.",
                "answer_key": "TODO reasoning, conditional where the law is conditional.",
                "exceptions": "TODO carve-outs, or empty string if there genuinely are none.",
                "authorities": [
                    {
                        "doc_id": provision["id"],
                        "citation": provision["citation"],
                        "role": "controlling",
                        "quote": quote,
                        "source_url": provision["source_url"],
                    }
                ],
                "difficulty": 2,
                "_provision_text": " ".join(provision["text"].split())[:1200],
            }
        )

    out = pathlib.Path(args.out)
    out.write_text(json.dumps(drafts, indent=1, ensure_ascii=False) + "\n")

    print(f"{len(drafts)} scaffolds written to {out}")
    print(f"{len(candidates)} candidates in {args.subject}; {skipped} skipped (no verified quote)")
    print("\nEvery quote below is already verified against the e-Library and the corpus.")
    for d in drafts:
        print(f"\n  {d['id']}  {d['authorities'][0]['citation']}")
        print(f"    quote: {d['authorities'][0]['quote'][:100]}")
    print("\nFill the TODO fields, drop _provision_text, append to bank/questions.json,")
    print("then run: python -m bank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
