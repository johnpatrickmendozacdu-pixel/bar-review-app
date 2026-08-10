# Case Corpus Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crawl Supreme Court e-Library decisions up to the 30 June 2025 coverage cut-off, subject-tagged, so answer-key reasoning has real jurisprudence to cite.

**Architecture:** A month-index crawler built on the existing `Fetcher`. It enumerates `/thebookshelf/docmonth/<Mon>/<YYYY>/1`, collects decision URLs, parses each with the existing `parse_case`, tags a subject by keyword, and feeds the existing `emit`. No new dependencies.

**Tech Stack:** Python 3.12+, `requests`, `beautifulsoup4`, `pytest`. Same three pinned dependencies as Phase 1.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-10-study-experience-design.md` and Phase 1:

- **Coverage cut-off:** every ingested case must have `promulgation_date` on or before **2025-06-30**. Later cases are discarded, not stored.
- **TLS:** the e-Library needs `certs/elibrary-chain.pem`. **Never** `verify=False`.
- **Politeness:** minimum 1 request per 2 seconds per host (`config.RATE_LIMIT_SECONDS`), descriptive User-Agent. This is a government server.
- **Shrink check:** a run producing materially fewer documents than the last good run must refuse to write.
- **No network access in tests.** All tests use committed fixtures or stubs.
- **Subjects** must be one of: `remedial`, `civil`, `commercial_tax`, `political`, `labor`, `criminal`.
- Dependencies kept near-zero and pinned.

---

## File Structure

| File | Responsibility |
|---|---|
| `ingest/crawl_elibrary.py` | Month-index enumeration → decision URLs. No parsing, no I/O beyond the injected fetcher |
| `ingest/subjects.py` | Keyword-based subject tagging for a decision |
| `ingest/__main__.py` | Modified: add a `--cases` mode that crawls before emitting |
| `tests/test_crawl_elibrary.py` | Crawler tests against the committed month fixture |
| `tests/test_subjects.py` | Tagging tests |

---

### Task 1: Month-index crawler

**Files:**
- Create: `ingest/crawl_elibrary.py`
- Test: `tests/test_crawl_elibrary.py`

**Interfaces:**
- Consumes: `Fetcher.get(url) -> str` from `ingest/fetch.py`
- Produces:
  - `month_url(year: int, month: int) -> str`
  - `parse_month_index(html: str) -> list[str]` — decision URLs, deduped, order preserved
  - `months_until(cutoff: datetime.date, years_back: int) -> list[tuple[int, int]]` — `(year, month)` pairs, newest first, none after cutoff
  - `crawl_decision_urls(fetcher, cutoff, years_back, limit) -> list[str]`

The existing fixture `tests/fixtures/elibrary_month.html` is a real June 2025 index page. It is the contract.

- [ ] **Step 1: Write the failing test**

```python
import datetime
import pathlib

import pytest

from ingest.crawl_elibrary import (
    crawl_decision_urls,
    month_url,
    months_until,
    parse_month_index,
)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "elibrary_month.html"
CUTOFF = datetime.date(2025, 6, 30)


class StubFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


def test_month_url_uses_the_three_letter_month():
    assert month_url(2025, 6) == (
        "https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/Jun/2025/1"
    )


def test_month_url_handles_every_month():
    assert month_url(2024, 1).endswith("/Jan/2024/1")
    assert month_url(2024, 12).endswith("/Dec/2024/1")


def test_parse_month_index_finds_decision_urls():
    html = FIXTURE.read_text(encoding="utf-8", errors="replace")
    urls = parse_month_index(html)
    assert urls, "the June 2025 fixture contains at least one decision"
    assert all("showdocs" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)


def test_parse_month_index_deduplicates():
    html = (
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/1">a</a>'
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/1">a</a>'
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/2">b</a>'
    )
    assert len(parse_month_index(html)) == 2


def test_parse_month_index_ignores_non_decision_links():
    html = '<a href="/thebookshelf/2">Republic Acts</a><a href="/about">About</a>'
    assert parse_month_index(html) == []


def test_months_until_never_returns_a_month_after_the_cutoff():
    months = months_until(CUTOFF, years_back=2)
    assert (2025, 7) not in months
    assert (2026, 1) not in months
    assert (2025, 6) in months


def test_months_until_is_newest_first():
    months = months_until(CUTOFF, years_back=2)
    assert months[0] == (2025, 6)
    assert months[1] == (2025, 5)


def test_months_until_spans_the_requested_years():
    months = months_until(CUTOFF, years_back=2)
    assert len(months) == 24
    assert months[-1] == (2023, 7)


def test_crawl_collects_urls_across_months():
    pages = {
        month_url(2025, 6): '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/1">x</a>',
        month_url(2025, 5): '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/2">y</a>',
    }
    fetcher = StubFetcher(pages)
    urls = crawl_decision_urls(fetcher, CUTOFF, years_back=1, limit=10)
    assert len(urls) == 2


def test_crawl_stops_at_the_limit():
    pages = {
        month_url(2025, 6): "".join(
            f'<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{i}">x</a>'
            for i in range(10)
        )
    }
    urls = crawl_decision_urls(StubFetcher(pages), CUTOFF, years_back=1, limit=3)
    assert len(urls) == 3


def test_a_missing_month_page_does_not_abort_the_crawl():
    pages = {
        month_url(2025, 5): '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/2">y</a>'
    }
    urls = crawl_decision_urls(StubFetcher(pages), CUTOFF, years_back=1, limit=10)
    assert len(urls) == 1, "June 404s; May must still be collected"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_crawl_elibrary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.crawl_elibrary'`

- [ ] **Step 3: Write the crawler**

```python
"""Enumerate e-Library decisions by month. No parsing of decisions here."""

import datetime
import re
import sys

BASE = "https://elibrary.judiciary.gov.ph/thebookshelf"

MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

_DECISION_HREF = re.compile(r'href="([^"]*showdocs/\d+/\d+)"')


def month_url(year: int, month: int) -> str:
    return f"{BASE}/docmonth/{MONTH_ABBR[month - 1]}/{year}/1"


def parse_month_index(html: str) -> list[str]:
    """Decision URLs on a month index page, deduped, order preserved."""
    urls = []
    seen = set()
    for href in _DECISION_HREF.findall(html):
        url = href if href.startswith("http") else f"https://elibrary.judiciary.gov.ph{href}"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def months_until(cutoff: datetime.date, years_back: int) -> list[tuple[int, int]]:
    """(year, month) pairs ending at the cut-off month, newest first."""
    months = []
    year, month = cutoff.year, cutoff.month
    for _ in range(years_back * 12):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months


def crawl_decision_urls(fetcher, cutoff: datetime.date, years_back: int, limit: int) -> list[str]:
    """Decision URLs across months. One dead month must not abort the crawl."""
    urls = []
    for year, month in months_until(cutoff, years_back):
        if len(urls) >= limit:
            break
        try:
            html = fetcher.get(month_url(year, month))
        except Exception as exc:
            print(f"SKIP {year}-{month:02d}: {exc}", file=sys.stderr)
            continue
        for url in parse_month_index(html):
            if len(urls) >= limit:
                break
            urls.append(url)
    return urls
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_crawl_elibrary.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Commit**

```bash
git add ingest/crawl_elibrary.py tests/test_crawl_elibrary.py
git commit -m "feat: add e-library month-index crawler"
```

---

### Task 2: Subject tagging

**Files:**
- Create: `ingest/subjects.py`
- Test: `tests/test_subjects.py`

**Interfaces:**
- Consumes: nothing
- Produces: `tag_subject(text: str) -> str` returning one of the six subject slugs, or `""` when no keyword group clearly wins

Returning `""` matters: a wrongly-tagged case is worse than an untagged one, because it puts Criminal Law reasoning in front of someone studying Labor.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_subjects.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.subjects'`

- [ ] **Step 3: Write the tagger**

```python
"""Keyword-based subject tagging. Deliberately conservative: returns "" rather
than guess, because a misfiled case puts the wrong law in front of a student."""

import re

KEYWORDS = {
    "criminal": (
        "estafa", "revised penal code", "accused", "homicide", "murder",
        "theft", "robbery", "reclusion", "prision", "criminal liability",
        "bail", "acquitted", "conviction",
    ),
    "labor": (
        "nlrc", "illegal dismissal", "employee", "employer", "labor code",
        "employment", "backwages", "reinstatement", "union",
        "collective bargaining", "labor arbiter",
    ),
    "remedial": (
        "rule 65", "certiorari", "grave abuse of discretion", "rules of court",
        "motion to dismiss", "jurisdiction", "pleading", "appeal",
        "writ of execution", "cause of action", "res judicata",
    ),
    "civil": (
        "contract of sale", "obligation", "civil code", "damages",
        "succession", "usufruct", "easement", "lease", "mortgage",
        "prescription", "co-ownership", "donation",
    ),
    "political": (
        "constitutionality", "constitution", "due process", "public officer",
        "eminent domain", "police power", "election", "comelec",
        "administrative agency", "ombudsman", "separation of powers",
    ),
    "commercial_tax": (
        "corporation", "bir", "income tax", "value-added tax", "securities",
        "insurance", "negotiable instrument", "intellectual property",
        "trademark", "patent", "bank", "deficiency assessment",
    ),
}

# A winner must lead the runner-up by this much, otherwise we decline to tag.
MARGIN = 2


def tag_subject(text: str) -> str:
    lowered = text.lower()
    scores = {
        subject: sum(len(re.findall(re.escape(k), lowered)) for k in keys)
        for subject, keys in KEYWORDS.items()
    }
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, best_score = ranked[0]
    runner_up_score = ranked[1][1]
    if best_score == 0 or best_score - runner_up_score < MARGIN:
        return ""
    return best
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_subjects.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add ingest/subjects.py tests/test_subjects.py
git commit -m "feat: add conservative subject tagging for cases"
```

---

### Task 3: Wire the crawler into ingest

**Files:**
- Modify: `ingest/__main__.py`
- Test: `tests/test_main.py` (append)

**Interfaces:**
- Consumes: `crawl_decision_urls`, `tag_subject`, `parse_case`, `emit`
- Produces: `ingest_cases(fetcher, cutoff, years_back, limit) -> list[Document]` — cases past the cut-off are dropped, subjects tagged

- [ ] **Step 1: Write the failing test**

Append to `tests/test_main.py`:

```python
import datetime

from ingest.__main__ import ingest_cases

CUTOFF_DATE = datetime.date(2025, 6, 30)


def case_html(gr, month, year, body="The accused was charged with estafa under the Revised Penal Code. "):
    return (
        f"<html><title>G.R. No. {gr} - ALPHA VS. BETA D E C I S I O N</title><body>"
        f"<p>[ G.R. No. {gr}, {month} 3, {year} ]</p><p>{body * 60}</p></body></html>"
    )


class CrawlStub:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


def test_ingest_cases_drops_anything_after_the_cutoff():
    from ingest.crawl_elibrary import month_url

    index = '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/9">x</a>'
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/9": case_html(
            "999", "August", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert docs == [], "an August 2025 decision is past the June 2025 cut-off"


def test_ingest_cases_keeps_documents_within_the_fence():
    from ingest.crawl_elibrary import month_url

    index = '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/8">x</a>'
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/8": case_html(
            "888", "June", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert len(docs) == 1
    assert docs[0].citation == "G.R. No. 888"


def test_ingest_cases_tags_the_subject():
    from ingest.crawl_elibrary import month_url

    index = '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/7">x</a>'
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/7": case_html(
            "777", "June", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert docs[0].subject == "criminal"


def test_an_unparseable_case_does_not_abort_the_run():
    from ingest.crawl_elibrary import month_url

    index = (
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/6">a</a>'
        '<a href="https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/5">b</a>'
    )
    pages = {
        month_url(2025, 6): index,
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/6": "<html><body>no docket here</body></html>",
        "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/5": case_html(
            "555", "June", "2025"
        ),
    }
    docs = ingest_cases(CrawlStub(pages), CUTOFF_DATE, years_back=1, limit=5)
    assert len(docs) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_main.py -k ingest_cases -v`
Expected: FAIL — `ImportError: cannot import name 'ingest_cases'`

- [ ] **Step 3: Add `ingest_cases` to `ingest/__main__.py`**

Add these imports at the top of the file, after the existing imports:

```python
import datetime

from ingest.crawl_elibrary import crawl_decision_urls
from ingest.subjects import tag_subject
```

Add this function after `run`:

```python
def ingest_cases(fetcher, cutoff: datetime.date, years_back: int, limit: int) -> list:
    """Crawl, parse, date-fence and subject-tag e-Library decisions.

    A decision after the cut-off is dropped rather than stored: the 2026 Bar
    cannot test it, so it must never reach an answer key.
    """
    documents = []
    for url in crawl_decision_urls(fetcher, cutoff, years_back, limit):
        try:
            doc = parse_case(fetcher.get(url), url)
        except Exception as exc:
            print(f"FAILED {url}: {exc}", file=sys.stderr)
            continue
        if doc.promulgation_date > cutoff:
            print(f"PAST CUTOFF {doc.citation} ({doc.promulgation_date})", file=sys.stderr)
            continue
        doc.subject = tag_subject(doc.text)
        documents.append(doc)
    return documents
```

Add a `--cases` mode by replacing `main` with:

```python
def main() -> int:
    fetcher = Fetcher(pathlib.Path(".cache"))

    if "--cases" in sys.argv:
        limit = 200
        for arg in sys.argv:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        cases = ingest_cases(fetcher, config.COVERAGE_DATE, years_back=3, limit=limit)
        print(f"Ingested {len(cases)} cases within the cut-off.", file=sys.stderr)
        seeds = load_seeds(SEEDS_PATH)
        statutes = []
        for seed in seeds:
            if seed["source"] != "lawphil":
                continue
            try:
                doc = parse_statute(fetcher.get(seed["url"]), seed["url"])
                doc.subject = seed.get("subject", "")
                doc.short_title = seed.get("short", "")
                statutes.append(doc)
            except Exception as exc:
                print(f"FAILED {seed['url']}: {exc}", file=sys.stderr)
        manifest = emit(statutes + cases, CORPUS_DIR)
        provisions = [p for doc in statutes for p in split_provisions(doc)]
        pathlib.Path(CORPUS_DIR, "provisions.json").write_text(
            json.dumps(provisions, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        manifest["provisions"] = len(provisions)
        print(json.dumps(manifest, indent=1))
        return 0

    manifest = run(load_seeds(SEEDS_PATH), fetcher, CORPUS_DIR)
    print(json.dumps(manifest, indent=1))
    if manifest["failures"]:
        print(
            f"\n{len(manifest['failures'])} seed(s) failed. Corpus written from the rest.",
            file=sys.stderr,
        )
        return 1
    return 0
```

Add `from ingest import config` to the imports if it is not already present.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_main.py -v`
Expected: PASS — all tests in the file pass

- [ ] **Step 5: Run a small real crawl**

```bash
.venv/bin/python -m ingest --cases --limit=15
```

Expected: a manifest showing `case` count of roughly 15 and no failures. This takes about a minute because of the 2-second politeness delay.

Inspect the result:

```bash
.venv/bin/python -c "
import json, pathlib, collections
docs = json.loads(pathlib.Path('corpus/case.json').read_text())
print('cases:', len(docs))
print(collections.Counter(d['subject'] or '(untagged)' for d in docs))
for d in docs[:5]:
    print(f\"  {d['citation']:22} {d['promulgation_date']}  {d['subject'] or '-'}\")
"
```

Confirm by eye that no `promulgation_date` is after `2025-06-30`.

- [ ] **Step 6: Run the full suite and commit**

```bash
.venv/bin/pytest -q && node app/sm2.test.js
```

Expected: all pass.

```bash
git add ingest/ tests/ corpus/
git commit -m "feat: crawl and date-fence e-library case corpus"
```

---

### Task 4: Scheduled case refresh

**Files:**
- Modify: `.github/workflows/ingest.yml`

**Interfaces:**
- Consumes: `python -m ingest --cases`
- Produces: nothing consumed downstream

- [ ] **Step 1: Change the ingest step to crawl cases**

In `.github/workflows/ingest.yml`, replace the `Run ingest` step with:

```yaml
      - name: Run ingest
        id: ingest
        run: python -m ingest --cases --limit=300
        continue-on-error: true
```

- [ ] **Step 2: Validate the YAML**

```bash
.venv/bin/python -c "
import pathlib, yaml
for p in sorted(pathlib.Path('.github/workflows').glob('*.yml')):
    yaml.safe_load(p.read_text()); print('OK', p)
"
```

Expected: `OK` for both workflow files.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ingest.yml
git commit -m "ci: crawl cases on the scheduled ingest run"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| §9 case corpus expansion via month index | Task 1 |
| §9 subject tagging | Task 2 |
| §3 date fence at 2025-06-30 | Task 3 (drops post-cutoff cases) |
| Politeness, TLS bundle | Inherited from `Fetcher`, unchanged |
| No network in tests | Tasks 1–3 all use stubs and fixtures |
| Scheduled refresh | Task 4 |

**Deliberate limitations:**

- Subject tagging is keyword-based and returns `""` on a near tie. Some cases
  will be untagged; that is preferred over misfiling.
- The crawler takes the first page of each month index only. Months with
  paginated results yield partial coverage. *ponytail: single page per month;
  follow pagination when a subject runs short of cases.*
