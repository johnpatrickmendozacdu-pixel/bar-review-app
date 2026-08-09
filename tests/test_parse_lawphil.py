import datetime
import pathlib

import pytest

from ingest.parse_lawphil import parse_statute

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "lawphil_ra386.html"
URL = "https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html"


@pytest.fixture
def doc():
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    return parse_statute(html, URL)


def test_produces_a_valid_document(doc):
    doc.validate()


def test_type_is_statute(doc):
    assert doc.type == "statute"


def test_source_url_is_preserved(doc):
    assert doc.source_url == URL


def test_id_is_the_ra_slug(doc):
    assert doc.id == "ra-386"


def test_citation_is_the_republic_act_number(doc):
    assert doc.citation == "Republic Act No. 386"


def test_title_is_the_act_long_title(doc):
    assert "CIVIL CODE OF THE PHILIPPINES" in doc.title.upper()


def test_text_is_substantial(doc):
    assert len(doc.text) > 100_000, "the Civil Code should not parse down to a stub"


def test_text_has_no_html_tags(doc):
    assert "<" not in doc.text


def test_uses_the_approval_date_not_the_first_date_in_the_body():
    """The body cites the 1866 Spanish Civil Code before stating its own
    approval date at the end. Grabbing the first date would be wrong."""
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    doc = parse_statute(html, URL)
    assert doc.promulgation_date == datetime.date(1949, 6, 18)


def test_empty_html_raises_rather_than_returning_a_stub():
    with pytest.raises(ValueError):
        parse_statute("<html><body></body></html>", URL)


def test_statute_with_no_date_anywhere_raises():
    html = "<html><title>R.A. 999</title><body>Republic Act No. 999. Some text.</body></html>"
    with pytest.raises(ValueError, match="date"):
        parse_statute(html, URL)
