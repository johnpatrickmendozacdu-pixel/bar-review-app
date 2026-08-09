import datetime
import pathlib

import pytest

from ingest.parse_elibrary import parse_case

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "elibrary_case.html"
URL = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/70158"


@pytest.fixture
def doc():
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    return parse_case(html, URL)


def test_produces_a_valid_document(doc):
    doc.validate()


def test_type_is_case(doc):
    assert doc.type == "case"


def test_citation_is_the_gr_number(doc):
    assert doc.citation == "G.R. No. 279692"


def test_id_is_derived_from_the_gr_number(doc):
    assert doc.id == "gr-279692"


def test_promulgation_date_comes_from_the_canonical_bracket_line(doc):
    assert doc.promulgation_date == datetime.date(2025, 6, 11)


def test_title_names_the_parties(doc):
    assert "DOLOR" in doc.title.upper()


def test_title_is_not_absurdly_long(doc):
    assert len(doc.title) <= 300


def test_text_is_substantial(doc):
    assert len(doc.text) > 10_000


def test_text_has_no_html_tags(doc):
    assert "<" not in doc.text


def test_missing_gr_number_raises():
    with pytest.raises(ValueError, match="G.R."):
        parse_case("<html><body><p>Text with no docket at all.</p></body></html>", URL)


def test_gr_number_without_a_date_raises():
    html = "<html><body><p>G.R. No. 12345 decided at some point.</p></body></html>"
    with pytest.raises(ValueError, match="date"):
        parse_case(html, URL)


def test_title_has_no_broken_html_artifacts(doc):
    """The e-Library's own markup contains a malformed <BR> inside the title."""
    assert "BR>" not in doc.title
