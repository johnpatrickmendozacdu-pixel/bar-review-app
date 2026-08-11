import datetime
import json
import pathlib

from bank.validate import (
    build_index,
    build_parents,
    load_elibrary,
    load_superseded,
    validate_bank,
)

CUTOFF = datetime.date(2025, 6, 30)
BANK = pathlib.Path("bank/questions.json")


def test_the_shipped_bank_is_valid_json():
    items = json.loads(BANK.read_text(encoding="utf-8"))
    assert isinstance(items, list)


def test_every_shipped_item_passes_the_gate():
    """This is the test that stops a bad question reaching a student."""
    items = json.loads(BANK.read_text(encoding="utf-8"))
    index = build_index(pathlib.Path("corpus"))
    valid, errors = validate_bank(
        items,
        index,
        CUTOFF,
        load_superseded(pathlib.Path("bank/superseded.json")),
        load_elibrary(pathlib.Path("corpus/elibrary_statutes.json")),
        build_parents(pathlib.Path("corpus")),
    )
    assert not errors, "invalid items in the shipped bank:\n" + "\n".join(errors)
    assert len(valid) == len(items)
