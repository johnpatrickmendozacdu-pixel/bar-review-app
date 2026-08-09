"""The single definition of what a corpus document is."""

import dataclasses
import datetime

from ingest import config


@dataclasses.dataclass
class Document:
    id: str
    schema_version: int
    type: str
    title: str
    citation: str
    promulgation_date: datetime.date | None
    source_url: str
    text: str
    # Bar subject this document was seeded under. Drives the weighted study
    # queue. Optional: a document can be valid before it is classified.
    subject: str = ""
    # Human-readable short name used when citing provisions, e.g. "Civil Code"
    # gives "Civil Code, Art. 1191" instead of "Republic Act No. 386, Art. 1191".
    short_title: str = ""

    def validate(self) -> None:
        """Raise ValueError if this document is not fit to commit."""
        if not self.id or not self.id.strip():
            raise ValueError("id must be a non-empty string")
        if self.schema_version != config.SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {self.schema_version} != {config.SCHEMA_VERSION}"
            )
        if self.type not in config.DOCUMENT_TYPES:
            raise ValueError(
                f"type {self.type!r} not in {sorted(config.DOCUMENT_TYPES)}"
            )
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(self.promulgation_date, datetime.date):
            raise ValueError(
                "promulgation_date must be a date; the cutoff fence needs it"
            )
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"source_url must be http(s): {self.source_url!r}")
        if not self.text or not self.text.strip():
            raise ValueError(
                "text must be non-empty; an empty document is a failed scrape"
            )

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["promulgation_date"] = self.promulgation_date.isoformat()
        return d
