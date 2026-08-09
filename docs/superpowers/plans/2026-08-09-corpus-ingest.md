# Corpus Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled ingest pipeline that pulls Philippine statutes and jurisprudence from lawphil.net and the Supreme Court e-Library into dated, validated JSON shards committed to this repo.

**Architecture:** A small Python package (`ingest/`) with one module per responsibility: fetching (polite HTTP + TLS handling + disk cache), parsing (one parser per source, driven by saved HTML fixtures so tests never touch the network), and emitting (schema-validated JSON shards + manifest with a shrink check). A GitHub Actions workflow runs it on a schedule and commits the result. No network in any test.

**Tech Stack:** Python 3.14 (stdlib-first), `requests`, `beautifulsoup4`, `pytest`. Three dependencies, pinned. No database — the corpus is JSON files.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-09-bar-review-app-design.md`:

- **Coverage cutoff:** `coverage_date = 2025-06-30`. Documents carry `promulgation_date`; filtering happens at read time, but the date MUST be captured at ingest.
- **Document schema:** `{ id, schema_version, type, title, citation, promulgation_date, source_url, text }`
- **TLS:** the e-Library presents an incomplete certificate chain. Handle with an explicit, documented, pinned CA bundle. **Never** a blanket `verify=False`.
- **Politeness:** rate limit against government servers. Minimum 1 request per 2 seconds per host, with a descriptive User-Agent.
- **Shrink check:** a run producing materially fewer documents than the last good run MUST refuse to commit and open a GitHub issue.
- **Dependencies kept near-zero and pinned.**
- **No network access in tests.** All parser tests run against committed HTML fixtures.

---

## File Structure

| File | Responsibility |
|---|---|
| `ingest/config.py` | Every tunable: cutoff date, subject weights, rate limit, schema version, source URLs |
| `ingest/schema.py` | Document dataclass + validation. The single definition of what a document is |
| `ingest/fetch.py` | Polite HTTP: rate limiting, TLS bundle, disk cache. Knows nothing about law |
| `ingest/parse_lawphil.py` | lawphil HTML → Document. Pure function, no I/O |
| `ingest/parse_elibrary.py` | e-Library HTML → Document. Pure function, no I/O |
| `ingest/emit.py` | Documents → JSON shards + manifest, with shrink check |
| `ingest/__main__.py` | Orchestrator. Wires the above together |
| `ingest/seeds.json` | Syllabus-derived seed list of statutes and cases |
| `tests/fixtures/*.html` | Saved real pages. Committed. The contract parsers are tested against |
| `.github/workflows/ingest.yml` | Scheduled run + commit + issue-on-failure |

---

### Task 1: Project scaffold and document schema

**Files:**
- Create: `requirements.txt`
- Create: `ingest/__init__.py`
- Create: `ingest/config.py`
- Create: `ingest/schema.py`
- Create: `tests/__init__.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `Document` dataclass with fields `(id: str, schema_version: int, type: str, title: str, citation: str, promulgation_date: datetime.date, source_url: str, text: str)`; `Document.validate() -> None` raising `ValueError`; `Document.to_dict() -> dict`; `config.SCHEMA_VERSION: int`, `config.COVERAGE_DATE: datetime.date`, `config.RATE_LIMIT_SECONDS: float`, `config.USER_AGENT: str`, `config.SUBJECT_WEIGHTS: dict[str, float]`

- [ ] **Step 1: Create the virtualenv and dependency file**

Create `requirements.txt`:

```
requests==2.32.3
beautifulsoup4==4.12.3
pytest==8.3.4
```

Run:

```bash
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt && echo INSTALLED
```

Expected: `INSTALLED`

- [ ] **Step 2: Write the failing test**

Create `tests/__init__.py` (empty file) and `tests/test_schema.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest'`

- [ ] **Step 4: Write config**

Create `ingest/__init__.py` (empty file) and `ingest/config.py`:

```python
"""Every tunable value in the ingest pipeline. Change values here, not in code."""

import datetime

SCHEMA_VERSION = 1

# 2026 Bar: questions sourced only from law as of this date.
# Bar Bulletin No. 1, 16 October 2025.
COVERAGE_DATE = datetime.date(2025, 6, 30)

# Politeness: one request per this many seconds, per host.
RATE_LIMIT_SECONDS = 2.0

USER_AGENT = (
    "BarReviewApp/1.0 (personal law-study tool; "
    "https://github.com/YOUR_USERNAME/bar-review-app)"
)

# Official 2026 Bar subject weights (Bar Bulletin No. 1).
SUBJECT_WEIGHTS = {
    "remedial": 0.25,
    "civil": 0.20,
    "commercial_tax": 0.20,
    "political": 0.15,
    "labor": 0.10,
    "criminal": 0.10,
}

DOCUMENT_TYPES = frozenset({"statute", "case", "bar_question"})

# A run producing fewer than this fraction of the last good run's document
# count is treated as a broken scrape, not a real shrink.
SHRINK_THRESHOLD = 0.95
```

- [ ] **Step 5: Write the schema**

Create `ingest/schema.py`:

```python
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

    def validate(self) -> None:
        """Raise ValueError if this document is not fit to commit."""
        if not self.id or not self.id.strip():
            raise ValueError("id must be a non-empty string")
        if self.schema_version != config.SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {self.schema_version} != {config.SCHEMA_VERSION}"
            )
        if self.type not in config.DOCUMENT_TYPES:
            raise ValueError(f"type {self.type!r} not in {sorted(config.DOCUMENT_TYPES)}")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(self.promulgation_date, datetime.date):
            raise ValueError("promulgation_date must be a date; the cutoff fence needs it")
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"source_url must be http(s): {self.source_url!r}")
        if not self.text or not self.text.strip():
            raise ValueError("text must be non-empty; an empty document is a failed scrape")

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["promulgation_date"] = self.promulgation_date.isoformat()
        return d
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_schema.py -v`
Expected: PASS — 6 passed

- [ ] **Step 7: Add .gitignore and commit**

Create `.gitignore`:

```
.venv/
__pycache__/
*.pyc
.cache/
.DS_Store
```

```bash
git add .gitignore requirements.txt ingest/ tests/
git commit -m "feat: add corpus document schema and config"
```

---

### Task 2: Polite fetcher with TLS handling and disk cache

**Files:**
- Create: `ingest/fetch.py`
- Create: `certs/README.md`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: `config.RATE_LIMIT_SECONDS`, `config.USER_AGENT`
- Produces: `Fetcher(cache_dir: pathlib.Path, sleep=time.sleep)` with method `get(url: str) -> str` returning page text, caching by URL hash; raises `requests.HTTPError` on non-200

The `sleep` parameter is injected so tests can assert rate limiting without actually waiting.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fetch.py`:

```python
import pathlib

import pytest

from ingest.fetch import Fetcher, cache_key


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Stands in for requests.Session. Records every call."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.headers = {}

    def get(self, url, timeout=None, verify=None):
        self.calls.append(url)
        return FakeResponse(self.pages[url])


@pytest.fixture
def sleeps():
    recorded = []
    return recorded, recorded.append


def test_cache_key_is_stable_and_filesystem_safe():
    k = cache_key("https://lawphil.net/statutes/ra_386.html")
    assert k == cache_key("https://lawphil.net/statutes/ra_386.html")
    assert "/" not in k


def test_get_returns_page_text(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "<html>A</html>"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    assert f.get("https://example.com/a") == "<html>A</html>"


def test_second_call_hits_disk_cache_not_network(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "<html>A</html>"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://example.com/a")
    f.get("https://example.com/a")
    assert session.calls == ["https://example.com/a"]


def test_cache_survives_a_new_fetcher_instance(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "<html>A</html>"})
    Fetcher(tmp_path, session=session, sleep=sleep).get("https://example.com/a")

    empty = FakeSession({})
    assert Fetcher(tmp_path, session=empty, sleep=sleep).get(
        "https://example.com/a"
    ) == "<html>A</html>"
    assert empty.calls == []


def test_rate_limit_sleeps_between_network_calls(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession(
        {"https://example.com/a": "A", "https://example.com/b": "B"}
    )
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://example.com/a")
    f.get("https://example.com/b")
    assert len(recorded) == 2
    assert all(s > 0 for s in recorded)


def test_cached_reads_do_not_sleep(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "A"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://example.com/a")
    recorded.clear()
    f.get("https://example.com/a")
    assert recorded == []


def test_elibrary_urls_use_the_pinned_bundle(tmp_path, sleeps):
    recorded, sleep = sleeps

    captured = {}

    class VerifyRecordingSession(FakeSession):
        def get(self, url, timeout=None, verify=None):
            captured["verify"] = verify
            return super().get(url, timeout=timeout, verify=verify)

    session = VerifyRecordingSession(
        {"https://elibrary.judiciary.gov.ph/x": "<html>X</html>"}
    )
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://elibrary.judiciary.gov.ph/x")
    assert captured["verify"] is not False, "blanket verify=False is forbidden"
    assert str(captured["verify"]).endswith(".pem")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.fetch'`

- [ ] **Step 3: Write the fetcher**

Create `ingest/fetch.py`:

```python
"""Polite HTTP with a disk cache. Knows nothing about law."""

import hashlib
import pathlib
import time

import requests

from ingest import config

CERT_BUNDLE = pathlib.Path(__file__).parent.parent / "certs" / "elibrary-chain.pem"

# Hosts that serve an incomplete certificate chain and need the pinned bundle.
PINNED_HOSTS = ("elibrary.judiciary.gov.ph",)


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32] + ".html"


class Fetcher:
    def __init__(self, cache_dir: pathlib.Path, session=None, sleep=time.sleep):
        self.cache_dir = pathlib.Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sleep = sleep
        self.session = session or requests.Session()
        self.session.headers = {"User-Agent": config.USER_AGENT}

    def _verify_for(self, url: str):
        """Return the CA bundle to verify against. Never False."""
        if any(host in url for host in PINNED_HOSTS):
            return str(CERT_BUNDLE)
        return True

    def get(self, url: str) -> str:
        cached = self.cache_dir / cache_key(url)
        if cached.exists():
            return cached.read_text(encoding="utf-8")

        self.sleep(config.RATE_LIMIT_SECONDS)
        response = self.session.get(url, timeout=30, verify=self._verify_for(url))
        response.raise_for_status()
        cached.write_text(response.text, encoding="utf-8")
        return response.text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_fetch.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: Obtain the real certificate chain**

The e-Library serves an incomplete chain, which is why a plain fetch fails. Capture the chain it *does* serve, then append the missing intermediate from the issuing CA.

```bash
mkdir -p certs && openssl s_client -showcerts -servername elibrary.judiciary.gov.ph -connect elibrary.judiciary.gov.ph:443 </dev/null 2>/dev/null | openssl x509 -outform PEM > certs/elibrary-leaf.pem && openssl x509 -in certs/elibrary-leaf.pem -noout -issuer -dates
```

Expected: prints the issuer and validity dates. Note the issuer name — you need that CA's intermediate certificate.

Download the named intermediate from the CA's official repository, then build the bundle:

```bash
cat certs/elibrary-intermediate.pem certs/elibrary-leaf.pem > certs/elibrary-chain.pem && .venv/bin/python -c "
import requests
r = requests.get('https://elibrary.judiciary.gov.ph/', timeout=30, verify='certs/elibrary-chain.pem')
print('VERIFIED OK', r.status_code)
"
```

Expected: `VERIFIED OK 200`

If it still fails, **stop and report** — do not proceed by disabling verification. Record the exact error in `certs/README.md`.

- [ ] **Step 6: Document the cert situation**

Create `certs/README.md`:

```markdown
# Certificate bundle for the SC e-Library

`elibrary.judiciary.gov.ph` serves an incomplete TLS chain: it presents its
leaf certificate without the intermediate, so standard verification fails
with "unable to verify the first certificate".

`elibrary-chain.pem` supplies the missing intermediate so verification can
succeed normally. The certificate is still fully verified — we are only
supplying a link the server omits.

**Never replace this with `verify=False`.** That would accept any
certificate from any party, turning a cosmetic server misconfiguration into
a real vulnerability.

## Refreshing

Certificates expire. When ingest starts failing with a TLS error, re-run the
capture in Task 2 Step 5 of the ingest plan.
```

- [ ] **Step 7: Commit**

```bash
git add ingest/fetch.py tests/test_fetch.py certs/
git commit -m "feat: add polite fetcher with pinned cert bundle and disk cache"
```

---

### Task 3: Capture HTML fixtures

**Files:**
- Create: `tools/capture_fixture.py`
- Create: `tests/fixtures/lawphil_ra386.html`
- Create: `tests/fixtures/elibrary_case.html`
- Create: `tests/fixtures/README.md`

**Interfaces:**
- Consumes: `Fetcher` from Task 2
- Produces: committed HTML fixtures — the contract every parser test runs against

This task exists because we do not yet know these sites' markup, and guessing selectors is how scrapers silently break. Capture first, parse second.

- [ ] **Step 1: Write the capture tool**

Create `tools/capture_fixture.py`:

```python
"""Save a real page to tests/fixtures/ so parsers can be tested offline.

Usage: python -m tools.capture_fixture <url> <fixture-name>
"""

import pathlib
import sys

from ingest.fetch import Fetcher

FIXTURES = pathlib.Path(__file__).parent.parent / "tests" / "fixtures"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    url, name = sys.argv[1], sys.argv[2]
    FIXTURES.mkdir(parents=True, exist_ok=True)
    html = Fetcher(pathlib.Path(".cache")).get(url)
    out = FIXTURES / f"{name}.html"
    out.write_text(html, encoding="utf-8")
    print(f"Saved {len(html)} bytes to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Capture a lawphil statute**

```bash
.venv/bin/python -m tools.capture_fixture "https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html" lawphil_ra386
```

Expected: `Saved NNNNN bytes to .../tests/fixtures/lawphil_ra386.html`

If that URL 404s, browse `https://lawphil.net/statutes/` to find the current path for the Civil Code and use it. Record the working URL in the fixtures README.

- [ ] **Step 3: Capture an e-Library case**

Browse `https://elibrary.judiciary.gov.ph/` and pick any Supreme Court decision with a visible G.R. number and promulgation date. Then:

```bash
.venv/bin/python -m tools.capture_fixture "<the decision URL you picked>" elibrary_case
```

Expected: `Saved NNNNN bytes to .../tests/fixtures/elibrary_case.html`

- [ ] **Step 4: Inspect the markup and record the real selectors**

```bash
.venv/bin/python -c "
from bs4 import BeautifulSoup
import pathlib
for name in ('lawphil_ra386', 'elibrary_case'):
    html = pathlib.Path(f'tests/fixtures/{name}.html').read_text(encoding='utf-8', errors='replace')
    soup = BeautifulSoup(html, 'html.parser')
    print('===', name, '===')
    print('TITLE:', soup.title.string if soup.title else None)
    for tag in soup.find_all(['h1','h2','h3'])[:8]:
        print('  HEADING:', tag.get_text(strip=True)[:100])
    print('  TEXT SAMPLE:', soup.get_text(' ', strip=True)[:400])
"
```

Expected: prints headings and a text sample for each fixture. **Write down what you see** — Task 4 and Task 5 depend on these actual selectors, not assumed ones.

- [ ] **Step 5: Document the fixtures**

Create `tests/fixtures/README.md`:

```markdown
# HTML fixtures

Real pages, saved verbatim. Parser tests run against these so the test suite
never touches the network and never depends on a government server being up.

| Fixture | Source URL | Captured |
|---|---|---|
| `lawphil_ra386.html` | (record the URL you used) | (date) |
| `elibrary_case.html` | (record the URL you used) | (date) |

## Refreshing

When a parser breaks in production but passes locally, the site markup
changed. Re-capture with:

    python -m tools.capture_fixture <url> <name>

Then fix the parser until tests pass against the NEW fixture. Keep the old
fixture too if you still need to parse old pages.
```

Replace the parenthesised placeholders with the actual URLs and today's date.

- [ ] **Step 6: Commit**

```bash
git add tools/ tests/fixtures/
git commit -m "test: capture lawphil and e-library HTML fixtures"
```

---

### Task 4: lawphil statute parser

**Files:**
- Create: `ingest/parse_lawphil.py`
- Test: `tests/test_parse_lawphil.py`

**Interfaces:**
- Consumes: `Document` from Task 1, `tests/fixtures/lawphil_ra386.html` from Task 3
- Produces: `parse_statute(html: str, source_url: str) -> Document` — a pure function, no I/O

- [ ] **Step 1: Write the failing test**

Create `tests/test_parse_lawphil.py`:

```python
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


def test_text_is_substantial(doc):
    assert len(doc.text) > 1000, "a statute should not parse down to a stub"


def test_text_has_no_html_tags(doc):
    assert "<" not in doc.text


def test_promulgation_date_is_extracted(doc):
    assert isinstance(doc.promulgation_date, datetime.date)


def test_id_is_slug_like(doc):
    assert doc.id == doc.id.lower()
    assert " " not in doc.id


def test_empty_html_raises_rather_than_returning_a_stub():
    with pytest.raises(ValueError):
        parse_statute("<html><body></body></html>", URL)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_parse_lawphil.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parse_lawphil'`

- [ ] **Step 3: Write the parser**

Create `ingest/parse_lawphil.py`:

```python
"""lawphil.net HTML -> Document. Pure function, no I/O."""

import datetime
import re

from bs4 import BeautifulSoup

from ingest import config
from ingest.schema import Document

# "June 18, 1949" or "18 June 1949"
_DATE_PATTERNS = (
    (r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", "%B %d %Y"),
    (r"(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})", "%d %B %Y"),
)

_RA_PATTERN = re.compile(r"Republic Act No\.?\s*(\d+)", re.IGNORECASE)


def _extract_date(text: str) -> datetime.date | None:
    for pattern, fmt in _DATE_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return datetime.datetime.strptime(" ".join(match.groups()), fmt).date()
        except ValueError:
            continue
    return None


def _slug(citation: str, title: str) -> str:
    ra = _RA_PATTERN.search(citation) or _RA_PATTERN.search(title)
    if ra:
        return f"ra-{ra.group(1)}"
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]


def parse_statute(html: str, source_url: str) -> Document:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    if not text.strip():
        raise ValueError(f"no text parsed from {source_url}; markup may have changed")

    title = (soup.title.string or "").strip() if soup.title else ""
    if not title:
        heading = soup.find(["h1", "h2", "h3"])
        title = heading.get_text(strip=True) if heading else ""
    if not title:
        raise ValueError(f"no title parsed from {source_url}")

    citation_match = _RA_PATTERN.search(text[:2000])
    citation = citation_match.group(0) if citation_match else title

    date = _extract_date(text[:4000])
    if date is None:
        raise ValueError(
            f"no promulgation date parsed from {source_url}; "
            "the cutoff fence cannot work without it"
        )

    return Document(
        id=_slug(citation, title),
        schema_version=config.SCHEMA_VERSION,
        type="statute",
        title=title,
        citation=citation,
        promulgation_date=date,
        source_url=source_url,
        text=text,
    )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_parse_lawphil.py -v`
Expected: PASS — 8 passed

If a test fails because the real markup differs from the assumptions above, **fix the parser to match the fixture** — the fixture is the truth, the parser is the guess.

- [ ] **Step 5: Commit**

```bash
git add ingest/parse_lawphil.py tests/test_parse_lawphil.py
git commit -m "feat: add lawphil statute parser"
```

---

### Task 5: e-Library case parser

**Files:**
- Create: `ingest/parse_elibrary.py`
- Test: `tests/test_parse_elibrary.py`

**Interfaces:**
- Consumes: `Document` from Task 1, `tests/fixtures/elibrary_case.html` from Task 3
- Produces: `parse_case(html: str, source_url: str) -> Document` — pure function, no I/O. `Document.citation` holds the G.R. number, `Document.id` is the slugified G.R. number.

- [ ] **Step 1: Write the failing test**

Create `tests/test_parse_elibrary.py`:

```python
import datetime
import pathlib

import pytest

from ingest.parse_elibrary import parse_case

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "elibrary_case.html"
URL = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/00000"


@pytest.fixture
def doc():
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    return parse_case(html, URL)


def test_produces_a_valid_document(doc):
    doc.validate()


def test_type_is_case(doc):
    assert doc.type == "case"


def test_citation_contains_gr_number(doc):
    assert "G.R." in doc.citation


def test_id_is_derived_from_gr_number(doc):
    assert doc.id.startswith("gr-")


def test_promulgation_date_is_a_real_date(doc):
    assert isinstance(doc.promulgation_date, datetime.date)
    assert 1900 < doc.promulgation_date.year <= datetime.date.today().year


def test_text_is_substantial(doc):
    assert len(doc.text) > 1000


def test_text_has_no_html_tags(doc):
    assert "<" not in doc.text


def test_missing_gr_number_raises():
    with pytest.raises(ValueError, match="G.R."):
        parse_case("<html><body><p>Some text with no docket.</p></body></html>", URL)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_parse_elibrary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parse_elibrary'`

- [ ] **Step 3: Write the parser**

Create `ingest/parse_elibrary.py`:

```python
"""SC e-Library HTML -> Document. Pure function, no I/O."""

import datetime
import re

from bs4 import BeautifulSoup

from ingest import config
from ingest.schema import Document

_GR_PATTERN = re.compile(r"G\.?\s*R\.?\s*(?:Nos?\.?)?\s*L?-?\s*(\d+)", re.IGNORECASE)

_DATE_PATTERNS = (
    (r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", "%B %d %Y"),
    (r"(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})", "%d %B %Y"),
)


def _extract_date(text: str) -> datetime.date | None:
    for pattern, fmt in _DATE_PATTERNS:
        for match in re.finditer(pattern, text):
            try:
                return datetime.datetime.strptime(" ".join(match.groups()), fmt).date()
            except ValueError:
                continue
    return None


def parse_case(html: str, source_url: str) -> Document:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    if not text.strip():
        raise ValueError(f"no text parsed from {source_url}; markup may have changed")

    gr = _GR_PATTERN.search(text)
    if not gr:
        raise ValueError(f"no G.R. number found in {source_url}")
    citation = gr.group(0).strip()

    date = _extract_date(text[:6000])
    if date is None:
        raise ValueError(
            f"no promulgation date parsed from {source_url}; "
            "the cutoff fence cannot work without it"
        )

    heading = soup.find(["h1", "h2", "h3"])
    title = heading.get_text(strip=True) if heading else ""
    if not title:
        title = (soup.title.string or "").strip() if soup.title else citation

    return Document(
        id=f"gr-{gr.group(1)}",
        schema_version=config.SCHEMA_VERSION,
        type="case",
        title=title,
        citation=citation,
        promulgation_date=date,
        source_url=source_url,
        text=text,
    )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_parse_elibrary.py -v`
Expected: PASS — 8 passed

Again: if the real markup differs, the fixture wins — adjust the parser.

- [ ] **Step 5: Commit**

```bash
git add ingest/parse_elibrary.py tests/test_parse_elibrary.py
git commit -m "feat: add e-library case parser"
```

---

### Task 6: Emit shards with the shrink check

**Files:**
- Create: `ingest/emit.py`
- Test: `tests/test_emit.py`

**Interfaces:**
- Consumes: `Document` from Task 1, `config.SHRINK_THRESHOLD`
- Produces: `emit(documents: list[Document], out_dir: pathlib.Path) -> dict` writing `out_dir/<type>.json` per document type plus `out_dir/manifest.json`, returning the manifest; raises `ShrinkError` when the new corpus is materially smaller than the existing manifest's count

Manifest shape: `{"schema_version": int, "generated_at": str, "counts": {type: int}, "total": int}`

- [ ] **Step 1: Write the failing test**

Create `tests/test_emit.py`:

```python
import datetime
import json

import pytest

from ingest.emit import ShrinkError, emit
from ingest.schema import Document


def make_docs(n, type_="statute"):
    return [
        Document(
            id=f"doc-{i}",
            schema_version=1,
            type=type_,
            title=f"Doc {i}",
            citation=f"Cite {i}",
            promulgation_date=datetime.date(2020, 1, 1),
            source_url="https://example.com/x",
            text="body text " * 20,
        )
        for i in range(n)
    ]


def test_writes_one_shard_per_type(tmp_path):
    emit(make_docs(3, "statute") + make_docs(2, "case"), tmp_path)
    assert (tmp_path / "statute.json").exists()
    assert (tmp_path / "case.json").exists()


def test_manifest_records_counts(tmp_path):
    manifest = emit(make_docs(3, "statute") + make_docs(2, "case"), tmp_path)
    assert manifest["counts"] == {"statute": 3, "case": 2}
    assert manifest["total"] == 5


def test_shard_contents_are_serialized_documents(tmp_path):
    emit(make_docs(1), tmp_path)
    data = json.loads((tmp_path / "statute.json").read_text())
    assert data[0]["id"] == "doc-0"
    assert data[0]["promulgation_date"] == "2020-01-01"


def test_invalid_document_is_rejected_before_writing(tmp_path):
    bad = make_docs(1)
    bad[0].text = ""
    with pytest.raises(ValueError, match="text"):
        emit(bad, tmp_path)
    assert not (tmp_path / "statute.json").exists()


def test_growth_is_allowed(tmp_path):
    emit(make_docs(10), tmp_path)
    manifest = emit(make_docs(20), tmp_path)
    assert manifest["total"] == 20


def test_material_shrink_raises_and_leaves_old_corpus_intact(tmp_path):
    emit(make_docs(100), tmp_path)
    with pytest.raises(ShrinkError, match="100"):
        emit(make_docs(10), tmp_path)
    data = json.loads((tmp_path / "statute.json").read_text())
    assert len(data) == 100, "the last good corpus must survive a failed run"


def test_trivial_shrink_within_threshold_is_allowed(tmp_path):
    emit(make_docs(100), tmp_path)
    manifest = emit(make_docs(97), tmp_path)
    assert manifest["total"] == 97


def test_empty_corpus_is_always_rejected(tmp_path):
    with pytest.raises(ShrinkError):
        emit([], tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_emit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.emit'`

- [ ] **Step 3: Write the emitter**

Create `ingest/emit.py`:

```python
"""Documents -> JSON shards + manifest, refusing to commit a broken corpus."""

import collections
import datetime
import json
import pathlib

from ingest import config
from ingest.schema import Document


class ShrinkError(RuntimeError):
    """The new corpus is materially smaller than the last good one."""


def _load_previous_total(out_dir: pathlib.Path) -> int:
    manifest = out_dir / "manifest.json"
    if not manifest.exists():
        return 0
    return json.loads(manifest.read_text()).get("total", 0)


def emit(documents: list[Document], out_dir: pathlib.Path) -> dict:
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not documents:
        raise ShrinkError("refusing to write an empty corpus")

    # Validate everything BEFORE writing anything, so a bad document can never
    # replace a good shard.
    for doc in documents:
        doc.validate()

    previous = _load_previous_total(out_dir)
    if previous and len(documents) < previous * config.SHRINK_THRESHOLD:
        raise ShrinkError(
            f"corpus shrank from {previous} to {len(documents)} documents "
            f"(threshold {config.SHRINK_THRESHOLD:.0%}). "
            "This is a broken scrape until proven otherwise. Nothing written."
        )

    by_type = collections.defaultdict(list)
    for doc in documents:
        by_type[doc.type].append(doc.to_dict())

    for doc_type, docs in by_type.items():
        (out_dir / f"{doc_type}.json").write_text(
            json.dumps(docs, indent=1, ensure_ascii=False), encoding="utf-8"
        )

    manifest = {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "counts": {t: len(d) for t, d in by_type.items()},
        "total": len(documents),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8"
    )
    return manifest
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_emit.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add ingest/emit.py tests/test_emit.py
git commit -m "feat: emit corpus shards with shrink protection"
```

---

### Task 7: Seed list and orchestrator

**Files:**
- Create: `ingest/seeds.json`
- Create: `ingest/__main__.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: everything from Tasks 1–6
- Produces: `run(seeds: list[dict], fetcher, out_dir) -> dict` returning the manifest; `load_seeds(path) -> list[dict]`. Seed shape: `{"url": str, "source": "lawphil" | "elibrary", "subject": str}`

`run()` must not abort the whole ingest when one document fails — it collects failures and reports them, because one dead URL should never cost you the other 200 documents.

- [ ] **Step 1: Write the seed file**

Create `ingest/seeds.json`. Start deliberately small — a handful of documents you can verify by eye. Expand later as you study.

```json
[
  {
    "url": "https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html",
    "source": "lawphil",
    "subject": "civil"
  },
  {
    "url": "https://lawphil.net/statutes/acts/act1930/act_3815_1930.html",
    "source": "lawphil",
    "subject": "criminal"
  }
]
```

Verify each URL loads before committing it. Replace any that 404 with the current lawphil path.

- [ ] **Step 2: Write the failing test**

Create `tests/test_main.py`:

```python
import json
import pathlib

import pytest

from ingest.__main__ import load_seeds, run


class StubFetcher:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


STATUTE_HTML = """
<html><title>Republic Act No. 386 - Civil Code</title><body>
<p>Republic Act No. 386. Approved: June 18, 1949.</p>
<p>{body}</p></body></html>
""".format(body="Article text. " * 200)


def test_load_seeds_reads_the_shipped_file():
    seeds = load_seeds(pathlib.Path("ingest/seeds.json"))
    assert len(seeds) >= 1
    assert {"url", "source", "subject"} <= set(seeds[0])


def test_run_writes_a_corpus(tmp_path):
    seeds = [{"url": "https://lawphil.net/a", "source": "lawphil", "subject": "civil"}]
    fetcher = StubFetcher({"https://lawphil.net/a": STATUTE_HTML})
    manifest = run(seeds, fetcher, tmp_path)
    assert manifest["total"] == 1
    assert (tmp_path / "statute.json").exists()


def test_one_dead_url_does_not_lose_the_others(tmp_path):
    seeds = [
        {"url": "https://lawphil.net/a", "source": "lawphil", "subject": "civil"},
        {"url": "https://lawphil.net/dead", "source": "lawphil", "subject": "civil"},
    ]
    fetcher = StubFetcher({"https://lawphil.net/a": STATUTE_HTML})
    manifest = run(seeds, fetcher, tmp_path)
    assert manifest["total"] == 1
    assert manifest["failures"] == ["https://lawphil.net/dead"]


def test_all_seeds_failing_raises_rather_than_writing_nothing(tmp_path):
    seeds = [{"url": "https://lawphil.net/dead", "source": "lawphil", "subject": "civil"}]
    with pytest.raises(Exception):
        run(seeds, StubFetcher({}), tmp_path)


def test_unknown_source_is_rejected(tmp_path):
    seeds = [{"url": "https://x/a", "source": "wikipedia", "subject": "civil"}]
    with pytest.raises(ValueError, match="wikipedia"):
        run(seeds, StubFetcher({"https://x/a": STATUTE_HTML}), tmp_path)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.__main__'`

- [ ] **Step 4: Write the orchestrator**

Create `ingest/__main__.py`:

```python
"""Ingest orchestrator. Run with: python -m ingest"""

import json
import pathlib
import sys

from ingest.emit import emit
from ingest.fetch import Fetcher
from ingest.parse_elibrary import parse_case
from ingest.parse_lawphil import parse_statute

PARSERS = {"lawphil": parse_statute, "elibrary": parse_case}

CORPUS_DIR = pathlib.Path("corpus")
SEEDS_PATH = pathlib.Path("ingest/seeds.json")


def load_seeds(path: pathlib.Path) -> list[dict]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def run(seeds: list[dict], fetcher, out_dir: pathlib.Path) -> dict:
    documents = []
    failures = []

    for seed in seeds:
        source = seed["source"]
        if source not in PARSERS:
            raise ValueError(f"unknown source {source!r}; expected one of {sorted(PARSERS)}")
        try:
            html = fetcher.get(seed["url"])
            documents.append(PARSERS[source](html, seed["url"]))
        except Exception as exc:  # one bad URL must not cost us the rest
            print(f"FAILED {seed['url']}: {exc}", file=sys.stderr)
            failures.append(seed["url"])

    manifest = emit(documents, out_dir)
    manifest["failures"] = failures
    return manifest


def main() -> int:
    fetcher = Fetcher(pathlib.Path(".cache"))
    manifest = run(load_seeds(SEEDS_PATH), fetcher, CORPUS_DIR)
    print(json.dumps(manifest, indent=1))
    return 1 if manifest["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/test_main.py -v`
Expected: PASS — 5 passed

- [ ] **Step 6: Run the real ingest**

```bash
.venv/bin/python -m ingest && cat corpus/manifest.json
```

Expected: a manifest with `total` matching your seed count and `failures: []`. Inspect `corpus/statute.json` by eye — confirm the title, citation and date of one document against the live page.

- [ ] **Step 7: Run the full suite and commit**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass.

```bash
git add ingest/ tests/test_main.py corpus/
git commit -m "feat: add ingest orchestrator and seed corpus"
```

---

### Task 8: Scheduled GitHub Action

**Files:**
- Create: `.github/workflows/ingest.yml`
- Create: `.github/workflows/test.yml`

**Interfaces:**
- Consumes: `python -m ingest` from Task 7
- Produces: nothing consumed by later tasks — this is the delivery mechanism

- [ ] **Step 1: Write the test workflow**

Create `.github/workflows/test.yml`:

```yaml
name: tests

on: [push, pull_request]

jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest -v
```

- [ ] **Step 2: Write the ingest workflow**

Create `.github/workflows/ingest.yml`:

```yaml
name: ingest corpus

on:
  schedule:
    - cron: "0 18 * * 0"   # Sundays 18:00 UTC (Monday 02:00 Manila)
  workflow_dispatch:

permissions:
  contents: write
  issues: write

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install -r requirements.txt

      - name: Run ingest
        id: ingest
        run: python -m ingest
        continue-on-error: true

      - name: Commit corpus if it changed
        if: steps.ingest.outcome == 'success'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          if git diff --quiet corpus/; then
            echo "No corpus changes."
          else
            git add corpus/
            git commit -m "chore: update corpus $(date -u +%Y-%m-%d)"
            git push
          fi

      - name: Open an issue if ingest failed
        if: steps.ingest.outcome == 'failure'
        uses: actions/github-script@v7
        with:
          script: |
            const run = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Corpus ingest failed on ${new Date().toISOString().slice(0, 10)}`,
              body: [
                'The scheduled ingest run failed. The last good corpus is still being served.',
                '',
                `Run log: ${run}`,
                '',
                'Likely causes, in order:',
                '1. Source site markup changed — re-capture the fixture and fix the parser.',
                '2. The e-Library certificate expired — refresh `certs/elibrary-chain.pem`.',
                '3. Shrink check tripped — a scrape returned far fewer documents than usual.',
              ].join('\n'),
            });
```

Note `continue-on-error` plus the outcome checks: a failed ingest must **not** fail loudly-and-uselessly by leaving the repo half-updated. It leaves the last good corpus in place and files an issue.

- [ ] **Step 3: Verify the workflows are valid YAML**

```bash
.venv/bin/python -c "
import pathlib, sys
try:
    import yaml
except ImportError:
    sys.exit('run: .venv/bin/pip install pyyaml')
for p in pathlib.Path('.github/workflows').glob('*.yml'):
    yaml.safe_load(p.read_text())
    print('OK', p)
"
```

Expected: `OK .github/workflows/ingest.yml` and `OK .github/workflows/test.yml`

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "ci: add test and scheduled ingest workflows"
```

- [ ] **Step 5: Push and confirm the workflow runs**

Create the GitHub repo, push, then trigger the ingest workflow manually from the Actions tab (`workflow_dispatch`). Confirm it completes and either commits a corpus or files an issue.

---

## Self-Review

**Spec coverage for the corpus layer:**

| Spec requirement | Task |
|---|---|
| Document schema with `promulgation_date` | Task 1 |
| Cutoff fence needs dates captured | Tasks 1, 4, 5 (parsers raise if no date) |
| Pinned CA bundle, never `verify=False` | Task 2 (enforced by a test) |
| Polite rate limiting | Task 2 |
| lawphil statutes | Task 4 |
| e-Library jurisprudence | Task 5 |
| Shrink check, refuse to commit | Task 6 |
| Open a GitHub issue on failure | Task 8 |
| Last good corpus keeps serving | Task 6 (validate-before-write) + Task 8 |
| Scheduled auto-update | Task 8 |
| Syllabus-driven seeds | Task 7 |
| No network in tests | Tasks 2–7 all use stubs or fixtures |

**Deferred to later plans, deliberately:**

- **Bar question PDFs** from `sc.judiciary.gov.ph` — needs a PDF dependency and a different parser. Add when essay practice (Plan 4) needs them.
- **Search index** — the syllabus-driven corpus is small enough that client-side filtering over loaded shards is fine. *ponytail: linear client-side search; build an inverted index when the corpus passes a few thousand documents.*
- **On-demand lazy fetching** — Plan 2 can queue requested case URLs into `seeds.json` via a PR; the scheduled run picks them up.

**Known risk carried forward:** Tasks 4 and 5 contain parsers written against *assumed* markup. Task 3 captures the real fixtures first precisely so that Steps 4 of those tasks correct the guess. If the parsers need substantial rewriting, that is the plan working as designed, not the plan failing.
