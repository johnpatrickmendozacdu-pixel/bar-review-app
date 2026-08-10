import datetime
import json

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
