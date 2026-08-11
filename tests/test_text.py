from ingest.text import repair_mojibake

# Built from code points so the test file itself stays clean ASCII.
LEFT = "â"
RIGHT = "â"
APOS = "â"


def test_curly_quotes_are_repaired():
    broken = f"committed as follows: {LEFT}The undersigned{RIGHT}"
    assert repair_mojibake(broken) == "committed as follows: “The undersigned”"


def test_clean_text_is_left_alone():
    clean = "The power to rescind obligations is implied in reciprocal ones."
    assert repair_mojibake(clean) == clean


def test_plain_ascii_is_unchanged():
    assert repair_mojibake("SO ORDERED.") == "SO ORDERED."


def test_apostrophes_are_repaired():
    assert repair_mojibake(f"the Court{APOS}s ruling") == "the Court’s ruling"


def test_repair_never_raises_on_odd_input():
    repair_mojibake(f"mixed {LEFT} and ñ and 中文")
