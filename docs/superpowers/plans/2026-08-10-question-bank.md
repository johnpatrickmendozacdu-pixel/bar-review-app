# Question Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the validator that makes "accurate or it isn't asked" mechanically enforceable, then author an initial bank of scenario-based questions that passes it.

**Architecture:** A pure-Python validator with no dependencies beyond the corpus JSON. It checks citations resolve, quotes appear verbatim, dates fall inside the cut-off, and the schema is complete. Items are authored as JSON and validated in CI, so a bad bank cannot merge.

**Tech Stack:** Python 3.12+, `pytest`. No new dependencies.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-10-study-experience-design.md`:

- **Coverage cut-off:** every cited document must have `promulgation_date` on or before **2025-06-30**.
- **No runtime AI anywhere.** No live grading, no live generation, no API key for anyone.
- **Every quoted passage must appear as an exact substring** of the cited document's corpus text.
- **Subjects** must be one of: `remedial`, `civil`, `commercial_tax`, `political`, `labor`, `criminal`.
- **Item types** must be one of: `hypothetical`, `issue_spotting`, `essay`, `doctrine`.
- **Validation runs in CI**, so a malformed bank cannot merge.
- **Generated reasoning is a study aid, not authority.** The quoted law is the authority.
- No network access in tests.

---

## File Structure

| File | Responsibility |
|---|---|
| `bank/validate.py` | The four-check gate. Pure functions, no I/O beyond reading corpus JSON |
| `bank/questions.json` | The authored item bank |
| `bank/README.md` | How to author items and why each check exists |
| `tests/test_validate.py` | Validator tests, including deliberately-bad items |
| `.github/workflows/test.yml` | Modified: run bank validation in CI |

---

### Task 1: The validation gate

**Files:**
- Create: `bank/__init__.py`
- Create: `bank/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `corpus/statute.json`, `corpus/case.json`, `corpus/provisions.json`
- Produces:
  - `build_index(corpus_dir) -> dict[str, dict]` — maps `doc_id` and provision id to `{"text": str, "promulgation_date": datetime.date}`
  - `ValidationError(Exception)`
  - `validate_item(item: dict, index: dict, cutoff: datetime.date) -> None` — raises `ValidationError` with a specific message
  - `validate_bank(items: list[dict], index: dict, cutoff) -> tuple[list[dict], list[str]]` — returns `(valid_items, error_messages)`

Item schema, from spec §6:

```
{
  "id": str, "schema_version": 1, "type": str, "subject": str,
  "question": str, "answer_key": str,
  "authorities": [{"doc_id": str, "citation": str, "quote": str, "source_url": str}],
  "difficulty": int
}
```

- [ ] **Step 1: Write the failing test**

```python
import datetime
import json
import pathlib

import pytest

from bank.validate import (
    ValidationError,
    build_index,
    validate_bank,
    validate_item,
)

CUTOFF = datetime.date(2025, 6, 30)

INDEX = {
    "ra-386-art-1191": {
        "text": (
            "The power to rescind obligations is implied in reciprocal ones, "
            "in case one of the obligors should not comply with what is "
            "incumbent upon him."
        ),
        "promulgation_date": datetime.date(1949, 6, 18),
    },
    "gr-279692": {
        "text": "The writ of habeas corpus extends to all cases of illegal confinement.",
        "promulgation_date": datetime.date(2025, 6, 11),
    },
    "gr-999999": {
        "text": "A decision handed down well after the coverage cut-off.",
        "promulgation_date": datetime.date(2025, 12, 1),
    },
}


def item(**overrides):
    base = {
        "id": "q-civil-0001",
        "schema_version": 1,
        "type": "hypothetical",
        "subject": "civil",
        "question": "Ana sold a lot to Ben who stopped paying. May Ana rescind?",
        "answer_key": "Yes. Rescission is implied in reciprocal obligations.",
        "authorities": [
            {
                "doc_id": "ra-386-art-1191",
                "citation": "Civil Code, Art. 1191",
                "quote": "The power to rescind obligations is implied in reciprocal ones",
                "source_url": "https://lawphil.net/x",
            }
        ],
        "difficulty": 2,
    }
    base.update(overrides)
    return base


def test_a_well_formed_item_passes():
    validate_item(item(), INDEX, CUTOFF)


def test_unknown_doc_id_is_rejected():
    bad = item(authorities=[{**item()["authorities"][0], "doc_id": "ra-386-art-9999"}])
    with pytest.raises(ValidationError, match="not in the corpus"):
        validate_item(bad, INDEX, CUTOFF)


def test_a_fabricated_quote_is_rejected():
    """The strongest check: the quote must appear verbatim in the corpus."""
    bad = item(
        authorities=[
            {
                **item()["authorities"][0],
                "quote": "The power to rescind is absolute and may never be waived",
            }
        ]
    )
    with pytest.raises(ValidationError, match="not found verbatim"):
        validate_item(bad, INDEX, CUTOFF)


def test_a_quote_differing_by_one_word_is_rejected():
    bad = item(
        authorities=[
            {
                **item()["authorities"][0],
                "quote": "The power to rescind contracts is implied in reciprocal ones",
            }
        ]
    )
    with pytest.raises(ValidationError, match="not found verbatim"):
        validate_item(bad, INDEX, CUTOFF)


def test_quote_whitespace_differences_are_tolerated():
    ok = item(
        authorities=[
            {
                **item()["authorities"][0],
                "quote": "The power to rescind obligations   is implied\nin reciprocal ones",
            }
        ]
    )
    validate_item(ok, INDEX, CUTOFF)


def test_authority_past_the_cutoff_is_rejected():
    bad = item(
        authorities=[
            {
                "doc_id": "gr-999999",
                "citation": "G.R. No. 999999",
                "quote": "A decision handed down well after the coverage cut-off.",
                "source_url": "https://elibrary.judiciary.gov.ph/x",
            }
        ]
    )
    with pytest.raises(ValidationError, match="after the coverage cut-off"):
        validate_item(bad, INDEX, CUTOFF)


def test_an_item_with_no_authorities_is_rejected():
    with pytest.raises(ValidationError, match="at least one authority"):
        validate_item(item(authorities=[]), INDEX, CUTOFF)


def test_empty_question_is_rejected():
    with pytest.raises(ValidationError, match="question"):
        validate_item(item(question="   "), INDEX, CUTOFF)


def test_empty_answer_key_is_rejected():
    with pytest.raises(ValidationError, match="answer_key"):
        validate_item(item(answer_key=""), INDEX, CUTOFF)


def test_unknown_type_is_rejected():
    with pytest.raises(ValidationError, match="type"):
        validate_item(item(type="trivia"), INDEX, CUTOFF)


def test_unknown_subject_is_rejected():
    with pytest.raises(ValidationError, match="subject"):
        validate_item(item(subject="maritime"), INDEX, CUTOFF)


def test_difficulty_outside_one_to_three_is_rejected():
    with pytest.raises(ValidationError, match="difficulty"):
        validate_item(item(difficulty=7), INDEX, CUTOFF)


def test_a_quote_shorter_than_twenty_characters_is_rejected():
    """A two-word quote trivially appears in any text and proves nothing."""
    bad = item(authorities=[{**item()["authorities"][0], "quote": "The power"}])
    with pytest.raises(ValidationError, match="too short"):
        validate_item(bad, INDEX, CUTOFF)


def test_validate_bank_separates_good_from_bad():
    good = item(id="q-1")
    bad = item(id="q-2", question="")
    valid, errors = validate_bank([good, bad], INDEX, CUTOFF)
    assert len(valid) == 1
    assert valid[0]["id"] == "q-1"
    assert len(errors) == 1
    assert "q-2" in errors[0]


def test_duplicate_ids_are_reported():
    valid, errors = validate_bank([item(id="q-1"), item(id="q-1")], INDEX, CUTOFF)
    assert any("duplicate" in e for e in errors)


def test_build_index_reads_the_real_corpus(tmp_path):
    (tmp_path / "statute.json").write_text(
        json.dumps(
            [
                {
                    "id": "ra-1",
                    "text": "Some statutory text.",
                    "promulgation_date": "1949-06-18",
                }
            ]
        )
    )
    (tmp_path / "provisions.json").write_text(
        json.dumps(
            [
                {
                    "id": "ra-1-art-1",
                    "text": "Article text.",
                    "promulgation_date": "1949-06-18",
                }
            ]
        )
    )
    index = build_index(tmp_path)
    assert "ra-1" in index
    assert "ra-1-art-1" in index
    assert index["ra-1"]["promulgation_date"] == datetime.date(1949, 6, 18)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bank'`

- [ ] **Step 3: Write the validator**

Create `bank/__init__.py` (empty file) and `bank/validate.py`:

```python
"""The gate that makes "accurate or it isn't asked" mechanical.

Nothing here trusts an author's good intentions. Every claim an item makes
about the law is checked against the corpus text itself.
"""

import collections
import datetime
import json
import pathlib

TYPES = frozenset({"hypothetical", "issue_spotting", "essay", "doctrine"})
SUBJECTS = frozenset(
    {"remedial", "civil", "commercial_tax", "political", "labor", "criminal"}
)

# Shorter than this and a "quote" is a common phrase that would appear in any
# legal text — it proves nothing about grounding.
MIN_QUOTE_LENGTH = 20


class ValidationError(Exception):
    """An item failed a check and must not be shipped."""


def _normalise(text: str) -> str:
    """Collapse whitespace so line wrapping does not defeat a real quote."""
    return " ".join(text.split())


def build_index(corpus_dir) -> dict:
    """Map every document and provision id to its text and date."""
    corpus_dir = pathlib.Path(corpus_dir)
    index = {}
    for name in ("statute.json", "case.json", "provisions.json"):
        path = corpus_dir / name
        if not path.exists():
            continue
        for doc in json.loads(path.read_text(encoding="utf-8")):
            index[doc["id"]] = {
                "text": doc["text"],
                "promulgation_date": datetime.date.fromisoformat(
                    doc["promulgation_date"]
                ),
            }
    return index


def validate_item(item: dict, index: dict, cutoff: datetime.date) -> None:
    item_id = item.get("id", "<no id>")

    def fail(message):
        raise ValidationError(f"{item_id}: {message}")

    if item.get("type") not in TYPES:
        fail(f"type {item.get('type')!r} not in {sorted(TYPES)}")
    if item.get("subject") not in SUBJECTS:
        fail(f"subject {item.get('subject')!r} not in {sorted(SUBJECTS)}")
    if not str(item.get("question", "")).strip():
        fail("question must not be empty")
    if not str(item.get("answer_key", "")).strip():
        fail("answer_key must not be empty")
    if item.get("difficulty") not in (1, 2, 3):
        fail(f"difficulty {item.get('difficulty')!r} must be 1, 2 or 3")

    authorities = item.get("authorities") or []
    if not authorities:
        fail("must cite at least one authority")

    for authority in authorities:
        doc_id = authority.get("doc_id")
        if doc_id not in index:
            fail(f"cited document {doc_id!r} is not in the corpus")

        entry = index[doc_id]
        if entry["promulgation_date"] > cutoff:
            fail(
                f"{doc_id} is dated {entry['promulgation_date']}, "
                f"after the coverage cut-off {cutoff}"
            )

        quote = _normalise(str(authority.get("quote", "")))
        if len(quote) < MIN_QUOTE_LENGTH:
            fail(f"quote for {doc_id} is too short to prove grounding: {quote!r}")
        if quote not in _normalise(entry["text"]):
            fail(f"quote for {doc_id} was not found verbatim in the corpus: {quote[:60]!r}")


def validate_bank(items, index, cutoff):
    """Return (valid_items, error_messages). Bad items are dropped, not fixed."""
    valid = []
    errors = []

    counts = collections.Counter(i.get("id") for i in items)
    for item_id, n in counts.items():
        if n > 1:
            errors.append(f"{item_id}: duplicate id appears {n} times")

    for item in items:
        try:
            validate_item(item, index, cutoff)
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        valid.append(item)

    return valid, errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_validate.py -v`
Expected: PASS — 16 passed

- [ ] **Step 5: Commit**

```bash
git add bank/ tests/test_validate.py
git commit -m "feat: add question bank validation gate"
```

---

### Task 2: Bank file, CLI check, and CI enforcement

**Files:**
- Create: `bank/questions.json`
- Create: `bank/__main__.py`
- Create: `bank/README.md`
- Modify: `.github/workflows/test.yml`
- Test: `tests/test_bank_file.py`

**Interfaces:**
- Consumes: `build_index`, `validate_bank` from Task 1
- Produces: `python -m bank` exiting non-zero when the shipped bank has any invalid item

- [ ] **Step 1: Create an empty bank**

Create `bank/questions.json`:

```json
[]
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_bank_file.py`:

```python
import datetime
import json
import pathlib

from bank.validate import build_index, validate_bank

CUTOFF = datetime.date(2025, 6, 30)
BANK = pathlib.Path("bank/questions.json")


def test_the_shipped_bank_is_valid_json():
    items = json.loads(BANK.read_text(encoding="utf-8"))
    assert isinstance(items, list)


def test_every_shipped_item_passes_the_gate():
    """This is the test that stops a bad question reaching a student."""
    items = json.loads(BANK.read_text(encoding="utf-8"))
    index = build_index(pathlib.Path("corpus"))
    valid, errors = validate_bank(items, index, CUTOFF)
    assert not errors, "invalid items in the shipped bank:\n" + "\n".join(errors)
    assert len(valid) == len(items)
```

- [ ] **Step 3: Run tests**

Run: `.venv/bin/pytest tests/test_bank_file.py -v`
Expected: PASS — 2 passed (an empty bank is trivially valid)

- [ ] **Step 4: Write the CLI**

Create `bank/__main__.py`:

```python
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
```

- [ ] **Step 5: Run it**

Run: `.venv/bin/python -m bank`
Expected: `0 valid, 0 rejected, NNNN corpus documents` and exit code 0

- [ ] **Step 6: Enforce in CI**

In `.github/workflows/test.yml`, add this step to the `pytest` job, after `- run: pytest -v`:

```yaml
      - run: python -m bank
```

- [ ] **Step 7: Document authoring**

Create `bank/README.md`:

```markdown
# Question bank

Scenario-based practice questions. Authored by hand (in Claude Code sessions),
validated mechanically, shipped as static JSON. There is no API key, no
generation service, and no runtime AI.

## The gate

`python -m bank` runs four checks per item. CI runs it on every push, so an
invalid bank cannot merge.

1. **Citations resolve.** Every `doc_id` exists in the corpus index.
2. **Quotes are verbatim.** Every `quote` appears as an exact substring of that
   document's corpus text, after whitespace normalisation. This is the check
   that makes fabricated authority impossible rather than unlikely.
3. **Date fence.** Every cited document is dated on or before 2025-06-30.
4. **Schema.** Type, subject, difficulty, question and answer key all valid.

A failing item is dropped and reported. It is never repaired automatically.

## Item shape

    {
      "id": "q-civil-0001",
      "schema_version": 1,
      "type": "hypothetical",
      "subject": "civil",
      "question": "Ana agreed to sell her lot to Ben ...",
      "answer_key": "Yes to both. The power to rescind ...",
      "authorities": [
        {
          "doc_id": "ra-386-art-1191",
          "citation": "Civil Code, Art. 1191",
          "quote": "The power to rescind obligations is implied in reciprocal ones",
          "source_url": "https://lawphil.net/..."
        }
      ],
      "difficulty": 2
    }

`type` is one of `hypothetical`, `issue_spotting`, `essay`, `doctrine`.
`subject` is one of `remedial`, `civil`, `commercial_tax`, `political`,
`labor`, `criminal`. `difficulty` is 1, 2 or 3.

## Authoring rules

- **Copy quotes, never retype them.** Read the text from `corpus/` and paste it.
  A remembered quote will fail check 2, which is the point.
- **Skip provisions not worth testing.** Repealing clauses, effectivity dates
  and definitions produce no question. Forcing an item out of every provision
  is what made the first version of this app useless.
- **The answer key explains; the quote proves.** Reasoning in `answer_key` is a
  study aid. Only the quoted text is authority, and the UI says so.
- **One question, one call.** State the facts, then ask something specific
  enough to have a defensible answer.

## Adding items

Append to `questions.json`, then:

    python -m bank

Fix or delete anything reported before committing.
```

- [ ] **Step 8: Validate workflow YAML and commit**

```bash
.venv/bin/python -c "
import pathlib, yaml
for p in sorted(pathlib.Path('.github/workflows').glob('*.yml')):
    yaml.safe_load(p.read_text()); print('OK', p)
"
```

Expected: `OK` for both files.

```bash
git add bank/ tests/test_bank_file.py .github/workflows/test.yml
git commit -m "feat: ship validated question bank with CI enforcement"
```

---

### Task 3: Author the initial bank

**Files:**
- Modify: `bank/questions.json`

**Interfaces:**
- Consumes: `corpus/provisions.json`, `corpus/case.json`, `python -m bank`
- Produces: a bank of at least 60 valid items

- [ ] **Step 1: List the provisions worth testing**

```bash
.venv/bin/python -c "
import json, pathlib
provs = json.loads(pathlib.Path('corpus/provisions.json').read_text())
big = [p for p in provs if len(p['text']) > 300]
print(len(big), 'substantive provisions')
import collections
print(collections.Counter(p['subject'] for p in big))
"
```

Expected: a count per subject. These are the candidates — short provisions are
usually definitional.

- [ ] **Step 2: Read the exact text of a provision before writing about it**

For each item you intend to author:

```bash
.venv/bin/python -c "
import json, pathlib, sys
pid = sys.argv[1]
provs = json.loads(pathlib.Path('corpus/provisions.json').read_text())
p = [x for x in provs if x['id'] == pid][0]
print(p['citation']); print(); print(p['text'])
" ra-386-art-1191
```

Copy the quote from this output. Do not type it from memory — check 2 exists
precisely to catch that.

- [ ] **Step 3: Write items covering every subject present in the corpus**

Append items to `bank/questions.json` following the shape in `bank/README.md`.

Distribution target for the first bank, weighted toward the official exam
percentages but bounded by what the corpus actually contains:

| Subject | Items | Notes |
|---|---|---|
| `civil` | 25 | Corpus has ~2,250 provisions; richest source |
| `criminal` | 15 | Revised Penal Code |
| `commercial_tax` | 12 | IP Code |
| `political` | 8 | RA 6713 plus any tagged cases |
| `remedial` | as available | Only if the case corpus supplies material |
| `labor` | as available | Only if the case corpus supplies material |

Type mix across the bank: roughly 60% `hypothetical`, 20% `doctrine`,
15% `issue_spotting`, 5% `essay`.

Id convention: `q-<subject>-<4 digits>`, e.g. `q-civil-0001`.

- [ ] **Step 4: Validate after every batch of about ten items**

Run: `.venv/bin/python -m bank`
Expected: `N valid, 0 rejected`

If any item is rejected, the message names the item and the failing check. Fix
the quote by copying it from the corpus output in Step 2, or delete the item.
Never adjust the validator to accommodate an item.

- [ ] **Step 5: Confirm the whole bank passes and commit**

```bash
.venv/bin/pytest tests/test_bank_file.py -v && .venv/bin/python -m bank
```

Expected: tests pass, `0 rejected`.

```bash
git add bank/questions.json
git commit -m "content: author initial question bank"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| §5 check 1, citations resolve | Task 1 |
| §5 check 2, quotes verbatim | Task 1 |
| §5 check 3, date fence | Task 1 |
| §5 check 4, schema | Task 1 |
| §5 validation runs in CI | Task 2 |
| §6 four item types and schema | Task 1 (`TYPES`), Task 3 |
| §4 authored, no API key, skip allowed | Task 3, `bank/README.md` |
| §4 reasoning is a study aid | `bank/README.md`; UI labelling is in the app plan |

**Deliberate limitations:**

- Quote matching normalises whitespace but is otherwise exact. A quote whose
  punctuation differs from the corpus fails. That strictness is the feature.
- The bank starts at roughly 60 items and grows on demand.
