"""Split statutes into individual provisions — the unit a drill card tests.

A card's back is the provision's verbatim text, so accuracy is structural:
nothing is paraphrased, summarised, or generated.
"""

import re

from ingest.schema import Document

# Provision labels only count at the start of a line. Statutes reference other
# provisions mid-sentence constantly ("...as provided in Article 1191..."), and
# those must never start a new card.
_LABEL = re.compile(
    r"(?m)^(?P<kind>Article|Art\.|Section|Sec\.)\s+(?P<number>\d+(?:-[A-Z])?)\s*[.:]?\s*",
)

_KIND_SLUG = {"article": "art", "art.": "art", "section": "sec", "sec.": "sec"}
_KIND_CITE = {"art": "Art.", "sec": "Sec."}

# Below this, a "provision" is a heading fragment or a cross-reference stub,
# not a rule worth drilling.
MIN_TEXT_LENGTH = 40


def split_provisions(doc: Document) -> list[dict]:
    """Return one dict per provision. Non-statutes yield nothing."""
    if doc.type != "statute":
        return []

    matches = list(_LABEL.finditer(doc.text))
    if not matches:
        return []

    short = doc.short_title or doc.citation
    provisions = []
    seen = set()

    for i, match in enumerate(matches):
        # Text runs from the end of this label to the start of the next one.
        end = matches[i + 1].start() if i + 1 < len(matches) else len(doc.text)
        body = doc.text[match.end() : end].strip()

        if len(body) < MIN_TEXT_LENGTH:
            continue

        kind = _KIND_SLUG[match.group("kind").lower()]
        number = match.group("number")
        prov_id = f"{doc.id}-{kind}-{number}"

        # Statutes repeat labels in indexes and footnotes. The first occurrence
        # is the authoritative text.
        if prov_id in seen:
            continue
        seen.add(prov_id)

        provisions.append(
            {
                "id": prov_id,
                "doc_id": doc.id,
                "citation": f"{short}, {_KIND_CITE[kind]} {number}",
                "subject": doc.subject,
                "promulgation_date": doc.promulgation_date.isoformat(),
                "source_url": doc.source_url,
                "text": body,
            }
        )

    return provisions
