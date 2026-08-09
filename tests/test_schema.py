import datetime

import pytest

from ingest.schema import Document


def valid_doc(**overrides):
    defaults = dict(
        id="ra-386",
        schema_version=1,
        type="statute",
        title="Civil Code of the Philippines",
        citation="Republic Act No. 386",
        promulgation_date=datetime.date(1949, 6, 18),
        source_url="https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html",
        text="An Act to Ordain and Institute the Civil Code of the Philippines.",
    )
    defaults.update(overrides)
    return Document(**defaults)


def test_valid_document_passes_validation():
    valid_doc().validate()


def test_to_dict_serializes_date_as_iso_string():
    d = valid_doc().to_dict()
    assert d["promulgation_date"] == "1949-06-18"
    assert d["id"] == "ra-386"


def test_missing_promulgation_date_is_rejected():
    with pytest.raises(ValueError, match="promulgation_date"):
        valid_doc(promulgation_date=None).validate()


def test_empty_text_is_rejected():
    with pytest.raises(ValueError, match="text"):
        valid_doc(text="   ").validate()


def test_unknown_type_is_rejected():
    with pytest.raises(ValueError, match="type"):
        valid_doc(type="blogpost").validate()


def test_non_http_source_url_is_rejected():
    with pytest.raises(ValueError, match="source_url"):
        valid_doc(source_url="ftp://example.com/x").validate()
