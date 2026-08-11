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


def test_title_stops_before_structural_headings(doc):
    """The long title runs into 'PRELIMINARY TITLE CHAPTER 1' in the raw text."""
    assert "PRELIMINARY TITLE" not in doc.title.upper()
    assert "CHAPTER" not in doc.title.upper()


def test_presidential_decree_is_recognised():
    html = (
        "<html><title>P.D. 442</title><body><p>PRESIDENTIAL DECREE NO. 442 "
        "A DECREE INSTITUTING A LABOR CODE</p><p>"
        + ("Article text here. " * 60)
        + "</p><p>Done in the City of Manila, this 1st day of May, 1974.</p></body></html>"
    )
    doc = parse_statute(html, URL)
    assert doc.id == "pd-442"
    assert doc.citation == "Presidential Decree No. 442"


def test_batas_pambansa_is_recognised():
    html = (
        "<html><title>B.P. 129</title><body><p>BATAS PAMBANSA BLG. 129 "
        "AN ACT REORGANIZING THE JUDICIARY</p><p>"
        + ("Section text. " * 60)
        + "</p><p>Approved: August 14, 1981.</p></body></html>"
    )
    doc = parse_statute(html, URL)
    assert doc.id == "bp-129"
    assert doc.citation == "Batas Pambansa Blg. 129"


def test_seed_metadata_supplies_a_date_the_text_lacks():
    """The Constitution carries no 'Approved:' line. A curated seed declares
    the ratification date rather than the parser guessing one."""
    html = "<html><title>Constitution</title><body><p>" + ("We the sovereign Filipino people. " * 60) + "</p></body></html>"
    doc = parse_statute(
        html,
        URL,
        meta={"id": "const-1987", "citation": "1987 Constitution", "date": "1987-02-02"},
    )
    assert doc.id == "const-1987"
    assert doc.promulgation_date == datetime.date(1987, 2, 2)


def test_declared_metadata_wins_over_inference():
    """A seed is curated with the document in hand; the parser is guessing.
    The Labor Code cites RA 6727 and the Rules of Court cite RA 6657, so
    inference from body text picks the WRONG document entirely."""
    html = (
        "<html><title>P.D. 442</title><body><p>PRESIDENTIAL DECREE NO. 442</p><p>"
        + ("As amended by Republic Act No. 6727 and Republic Act No. 6715. " * 40)
        + "</p><p>Approved: June 9, 1989.</p></body></html>"
    )
    doc = parse_statute(html, URL, meta={"id": "pd-442", "citation": "Presidential Decree No. 442", "date": "1974-05-01"})
    assert doc.id == "pd-442"
    assert doc.promulgation_date == datetime.date(1974, 5, 1)


def test_a_statute_number_cited_in_the_body_does_not_become_the_id():
    html = (
        "<html><title>P.D. 442</title><body><p>PRESIDENTIAL DECREE NO. 442 "
        "A DECREE INSTITUTING A LABOR CODE</p><p>"
        + ("This shall not impair Republic Act No. 6727. " * 60)
        + "</p><p>Done in the City of Manila, this 1st day of May, 1974.</p></body></html>"
    )
    doc = parse_statute(html, URL)
    assert doc.id == "pd-442", "RA 6727 is cited in the body, not the document's own number"



def test_a_document_with_no_recognisable_number_and_no_meta_still_raises():
    html = "<html><title>Something</title><body><p>" + ("Text. " * 60) + "</p><p>Approved: June 1, 2000.</p></body></html>"
    with pytest.raises(ValueError):
        parse_statute(html, URL)
