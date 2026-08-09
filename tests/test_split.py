import datetime
import json
import pathlib

import pytest

from ingest.schema import Document
from ingest.split import split_provisions


def statute(text, **kw):
    defaults = dict(
        id="ra-386",
        schema_version=1,
        type="statute",
        title="Civil Code",
        citation="Republic Act No. 386",
        promulgation_date=datetime.date(1949, 6, 18),
        source_url="https://lawphil.net/x",
        text=text,
        subject="civil",
        short_title="Civil Code",
    )
    defaults.update(kw)
    return Document(**defaults)


SIMPLE = "Preamble junk.\nArticle 1. This Act shall be known as the Civil Code.\nArticle 2. Laws shall take effect after fifteen days following publication."


def test_splits_on_article_boundaries():
    provs = split_provisions(statute(SIMPLE))
    assert len(provs) == 2


def test_provision_id_is_stable_and_slug_like():
    provs = split_provisions(statute(SIMPLE))
    assert provs[0]["id"] == "ra-386-art-1"


def test_citation_uses_the_short_title():
    provs = split_provisions(statute(SIMPLE))
    assert provs[0]["citation"] == "Civil Code, Art. 1"


def test_text_excludes_the_label_but_keeps_the_rule():
    provs = split_provisions(statute(SIMPLE))
    assert provs[0]["text"].startswith("This Act shall be known")
    assert "Article 1." not in provs[0]["text"]


def test_preamble_before_the_first_article_is_dropped():
    provs = split_provisions(statute(SIMPLE))
    assert all("Preamble junk" not in p["text"] for p in provs)


def test_subject_and_date_are_inherited():
    provs = split_provisions(statute(SIMPLE))
    assert provs[0]["subject"] == "civil"
    assert provs[0]["promulgation_date"] == "1949-06-18"
    assert provs[0]["doc_id"] == "ra-386"


def test_handles_section_style_statutes():
    text = (
        "Section 1. This Act shall be known as the Intellectual Property Code "
        "of the Philippines.\n"
        "Section 2. The declaration of state policy on intellectual property "
        "protection follows in this section."
    )
    provs = split_provisions(statute(text, id="ra-8293", short_title="IP Code"))
    assert len(provs) == 2
    assert provs[0]["id"] == "ra-8293-sec-1"
    assert provs[0]["citation"] == "IP Code, Sec. 1"


def test_mid_sentence_references_do_not_split():
    text = "Article 1. A rule that mentions Article 1191 and Section 5 inline without splitting."
    provs = split_provisions(statute(text))
    assert len(provs) == 1


def test_trivially_short_provisions_are_dropped():
    text = "Article 1. Short.\nArticle 2. This one is long enough to be a real rule worth drilling on."
    provs = split_provisions(statute(text))
    assert [p["id"] for p in provs] == ["ra-386-art-2"]


def test_duplicate_labels_keep_only_the_first():
    text = (
        "Article 1. The first and authoritative statement of this rule here.\n"
        "Article 1. A duplicate appearing in an index or footnote section here.\n"
    )
    provs = split_provisions(statute(text))
    assert len(provs) == 1
    assert "authoritative" in provs[0]["text"]


def test_non_statute_documents_yield_nothing():
    case = statute("Article 1. Something.", type="case", id="gr-1")
    assert split_provisions(case) == []


def test_real_civil_code_splits_into_thousands_of_articles():
    path = pathlib.Path("corpus/statute.json")
    if not path.exists():
        pytest.skip("corpus not built")
    raw = [d for d in json.loads(path.read_text()) if d["id"] == "ra-386"][0]
    doc = statute(raw["text"])
    provs = split_provisions(doc)
    assert 2000 < len(provs) < 2400, f"expected ~2270 Civil Code articles, got {len(provs)}"
    art1191 = [p for p in provs if p["id"] == "ra-386-art-1191"]
    assert art1191, "Article 1191 should be present"
    assert "power to rescind" in art1191[0]["text"]
