from ingest.subjects import tag_subject


def test_criminal_keywords_win():
    text = "The accused was charged with estafa under the Revised Penal Code. " * 3
    assert tag_subject(text) == "criminal"


def test_labor_keywords_win():
    text = "The employee filed for illegal dismissal before the NLRC. " * 3
    assert tag_subject(text) == "labor"


def test_remedial_keywords_win():
    text = "The petition for certiorari under Rule 65 alleges grave abuse of discretion. " * 3
    assert tag_subject(text) == "remedial"


def test_civil_keywords_win():
    text = "The contract of sale is void for lack of consideration and the obligation is extinguished. " * 3
    assert tag_subject(text) == "civil"


def test_political_keywords_win():
    text = "The constitutionality of the statute is challenged as a violation of due process. " * 3
    assert tag_subject(text) == "political"


def test_commercial_tax_keywords_win():
    text = "The corporation contests the deficiency income tax assessment by the BIR. " * 3
    assert tag_subject(text) == "commercial_tax"


def test_text_with_no_legal_keywords_is_untagged():
    assert tag_subject("The weather was pleasant and the meeting adjourned early.") == ""


def test_a_near_tie_is_untagged():
    """Mistagging is worse than not tagging — it misfiles study material."""
    text = "estafa contract"
    assert tag_subject(text) == ""


def test_tagging_is_case_insensitive():
    text = "THE ACCUSED WAS CHARGED WITH ESTAFA UNDER THE REVISED PENAL CODE. " * 3
    assert tag_subject(text) == "criminal"
