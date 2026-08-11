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


def item_v2(**overrides):
    base = item()
    base["schema_version"] = 2
    base["exceptions"] = "Art. 1484 governs instead for installment sales of personalty."
    base["authorities"][0]["role"] = "controlling"
    base.update(overrides)
    return base


def test_a_v2_item_with_roles_passes():
    validate_item(item_v2(), INDEX, CUTOFF)


def test_a_related_authority_is_validated_exactly_like_a_controlling_one():
    """A 'similar case' carries the same guarantee: real document, real quote."""
    bad = item_v2()
    bad["authorities"].append(
        {
            "doc_id": "gr-279692",
            "citation": "G.R. No. 279692",
            "quote": "This sentence was never written by any court anywhere",
            "source_url": "https://elibrary.judiciary.gov.ph/x",
            "role": "related",
        }
    )
    with pytest.raises(ValidationError, match="not found verbatim"):
        validate_item(bad, INDEX, CUTOFF)


def test_a_valid_related_authority_is_accepted():
    ok = item_v2()
    ok["authorities"].append(
        {
            "doc_id": "gr-279692",
            "citation": "G.R. No. 279692",
            "quote": "The writ of habeas corpus extends to all cases of illegal confinement",
            "source_url": "https://elibrary.judiciary.gov.ph/x",
            "role": "related",
        }
    )
    validate_item(ok, INDEX, CUTOFF)


def test_an_unknown_role_is_rejected():
    bad = item_v2()
    bad["authorities"][0]["role"] = "vaguely_relevant"
    with pytest.raises(ValidationError, match="role"):
        validate_item(bad, INDEX, CUTOFF)


def test_an_item_with_only_related_authorities_is_rejected():
    """Something must actually govern the answer."""
    bad = item_v2()
    bad["authorities"][0]["role"] = "related"
    with pytest.raises(ValidationError, match="controlling"):
        validate_item(bad, INDEX, CUTOFF)


def test_exceptions_may_be_empty_when_there_genuinely_are_none():
    validate_item(item_v2(exceptions=""), INDEX, CUTOFF)


SUPERSEDED = {
    "act-3815-art-315": {"reason": "Amounts amended by RA 10951.", "replaced_by": ["ra-10951"]},
    "pd-442-art-279": {"reason": "Renumbered to Art. 294.", "replaced_by": []},
}

INDEX_S = {
    **INDEX,
    "act-3815-art-315": {
        "text": "Any person who shall defraud another by any of the means mentioned hereinbelow shall be punished by",
        "promulgation_date": datetime.date(1930, 12, 8),
    },
    "ra-10951": {
        "text": "An Act adjusting the amount or the value of property and damage on which a penalty is based",
        "promulgation_date": datetime.date(2017, 8, 29),
    },
    "pd-442-art-279": {
        "text": "An employee who is unjustly dismissed from work shall be entitled to reinstatement",
        "promulgation_date": datetime.date(1974, 5, 1),
    },
}


def superseded_item(**overrides):
    base = item_v2()
    base["authorities"] = [
        {
            "doc_id": "act-3815-art-315",
            "citation": "Revised Penal Code, Art. 315",
            "role": "controlling",
            "quote": "Any person who shall defraud another by any of the means mentioned hereinbelow",
            "source_url": "https://lawphil.net/x",
        }
    ]
    base.update(overrides)
    return base


def test_citing_a_superseded_provision_alone_is_rejected():
    """A verbatim quote of amended law is still amended law."""
    with pytest.raises(ValidationError, match="superseded"):
        validate_item(superseded_item(), INDEX_S, CUTOFF, SUPERSEDED)


def test_citing_the_superseded_provision_with_its_replacement_is_allowed():
    ok = superseded_item()
    ok["authorities"].append(
        {
            "doc_id": "ra-10951",
            "citation": "Republic Act No. 10951",
            "role": "related",
            "quote": "An Act adjusting the amount or the value of property and damage on which a penalty is based",
            "source_url": "https://lawphil.net/y",
        }
    )
    validate_item(ok, INDEX_S, CUTOFF, SUPERSEDED)


def test_a_renumbered_provision_needs_no_replacement_but_must_be_flagged():
    """Renumbering keeps the substance, so an empty replaced_by list means the
    item may ship — the flag exists so the author knows to mention the number."""
    renamed = superseded_item()
    renamed["authorities"][0] = {
        "doc_id": "pd-442-art-279",
        "citation": "Labor Code, Art. 279",
        "role": "controlling",
        "quote": "An employee who is unjustly dismissed from work shall be entitled to reinstatement",
        "source_url": "https://lawphil.net/z",
    }
    validate_item(renamed, INDEX_S, CUTOFF, SUPERSEDED)


def test_an_unflagged_provision_is_unaffected():
    validate_item(item_v2(), INDEX_S, CUTOFF, SUPERSEDED)


from bank.validate import SIGNIFICANT

ELIBRARY = {
    "ra-386": {
        "url": "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/2/53360",
        "text": "ART. 20. Every person who, contrary to law, willfully or negligently causes damage to another, shall indemnify the latter for the same.",
    }
}

PARENTS = {"ra-386-art-20": "ra-386", "ra-386-art-1191": "ra-386"}


def el_item(quote):
    base = item_v2()
    base["authorities"] = [
        {
            "doc_id": "ra-386-art-20",
            "citation": "Civil Code, Art. 20",
            "role": "controlling",
            "quote": quote,
            "source_url": "https://lawphil.net/x",
        }
    ]
    return base


EL_INDEX = {
    **INDEX,
    "ra-386-art-20": {
        # lawphil's spelling, which is what the corpus holds.
        "text": "Every person who, contrary to law, wilfully or negligently causes damage to another. Every person who, contrary to law, willfully or negligently causes damage to another",
        "promulgation_date": datetime.date(1949, 6, 18),
    },
}


def test_a_quote_matching_lawphil_but_not_the_elibrary_is_rejected():
    """lawphil writes 'wilfully'; the Court's own copy writes 'willfully'.
    The e-Library is authoritative, so the lawphil spelling must fail."""
    bad = el_item("contrary to law, wilfully or negligently causes damage to another")
    with pytest.raises(ValidationError, match="e-Library"):
        validate_item(bad, EL_INDEX, CUTOFF, None, ELIBRARY, PARENTS)


def test_a_quote_matching_the_elibrary_passes():
    ok = el_item("contrary to law, willfully or negligently causes damage to another")
    validate_item(ok, EL_INDEX, CUTOFF, None, ELIBRARY, PARENTS)


def test_an_authority_with_no_elibrary_copy_fails_closed():
    """If the Court's copy cannot be checked, the item does not ship."""
    orphan = el_item("contrary to law, willfully or negligently causes damage to another")
    orphan["authorities"][0]["doc_id"] = "ra-6552-sec-3"
    index = {**EL_INDEX, "ra-6552-sec-3": {"text": "contrary to law, willfully or negligently causes damage to another", "promulgation_date": datetime.date(1972, 8, 26)}}
    with pytest.raises(ValidationError, match="no e-Library"):
        validate_item(orphan, index, CUTOFF, None, ELIBRARY, {"ra-6552-sec-3": "ra-6552"})


def test_elibrary_checking_is_skipped_when_no_registry_is_supplied():
    """Existing callers that pass no e-Library data keep working."""
    validate_item(item_v2(), INDEX, CUTOFF)


def test_insignificant_spelling_difference_between_sources_is_tolerated():
    """lawphil writes 'wilfully', the Court writes 'willfully'. Same premise."""
    from bank.validate import divergence

    assert divergence(
        "contrary to law, wilfully or negligently causes damage to another",
        "contrary to law, willfully or negligently causes damage to another",
    ) < SIGNIFICANT


def test_article_in_a_manner_variation_is_tolerated():
    from bank.validate import divergence

    assert divergence(
        "loss or injury to another in manner that is contrary to morals",
        "loss or injury to another in a manner that is contrary to morals",
    ) < SIGNIFICANT


def test_a_changed_qualifier_is_significant():
    """'without a definite period' narrows the rule. That is not cosmetic."""
    from bank.validate import divergence

    assert divergence(
        "An employer may terminate an employment for any of the following just causes",
        "An employer may terminate an employment without a definite period for any of the following just causes",
    ) >= SIGNIFICANT


def test_a_different_provision_entirely_is_significant():
    from bank.validate import divergence

    assert divergence(
        "The power to rescind obligations is implied in reciprocal ones",
        "Every person must act with justice and observe honesty and good faith",
    ) >= SIGNIFICANT


def test_quote_is_checked_against_the_elibrary_as_primary():
    """The Court's wording governs, even where lawphil differs."""
    ok = el_item("contrary to law, willfully or negligently causes damage to another")
    validate_item(ok, EL_INDEX, CUTOFF, None, ELIBRARY, PARENTS)
