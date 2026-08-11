from tools.scaffold import next_id, pick_quote, used_doc_ids

PROVISION = (
    "Termination by employer. An employer may terminate an employment for any "
    "of the following causes: serious misconduct or willful disobedience by the "
    "employee of the lawful orders of his employer. Gross and habitual neglect "
    "by the employee of his duties."
)


def test_a_quote_present_in_both_sources_is_chosen():
    quote = pick_quote(PROVISION, "prelude " + PROVISION + " postlude")
    assert quote
    assert quote in PROVISION


def test_no_quote_is_returned_when_the_primary_source_disagrees():
    """If the Court's text does not contain it, we must not scaffold it."""
    assert pick_quote(PROVISION, "An entirely different statute about fisheries.") is None


def test_quotes_shorter_than_the_floor_are_rejected():
    assert pick_quote("Too short.", "Too short.") is None


def test_the_longest_verified_span_wins():
    text = "Short clause here. A considerably longer clause that states the operative rule in full detail."
    quote = pick_quote(text, text)
    assert "considerably longer" in quote


def test_used_doc_ids_collects_every_authority():
    bank = [
        {"authorities": [{"doc_id": "a"}, {"doc_id": "b"}]},
        {"authorities": [{"doc_id": "c"}]},
    ]
    assert used_doc_ids(bank) == {"a", "b", "c"}


def test_next_id_continues_the_existing_sequence():
    bank = [{"id": "q-civil-0001"}, {"id": "q-civil-0007"}, {"id": "q-labor-0003"}]
    assert next_id(bank, "civil") == 8
    assert next_id(bank, "remedial") == 1
