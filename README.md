# Bar Review App

Philippine Bar review tool. **Phase 1 (corpus) and Phase 2 (drills) are built.**

## The app

Open `index.html` through any web server and you get spaced-repetition drills
over 2,878 statutory provisions. One card = one provision, and the answer is
the **verbatim text of the law** — nothing paraphrased, nothing generated, so
there is nothing to be wrong.

```bash
python3 -m http.server 8000   # then open http://localhost:8000
```

No build step. No framework. No `npm install`. Your progress lives in this
browser's localStorage and is never uploaded; Settings has a backup
export/restore.

Three grades — *Didn't know* / *Hard* / *Knew it* (keys `1` `2` `3`, space to
reveal). Cards you miss return before the session ends.

## What this does

Pulls Philippine statutes and Supreme Court decisions from official sources
into dated, validated JSON in `corpus/`. Every future question, answer key and
grade in the app must trace back to a document here — that is the accuracy
guarantee.

Sources:

- [lawphil.net](https://lawphil.net) — statutes
- [SC e-Library](https://elibrary.judiciary.gov.ph/) — jurisprudence

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest            # 67 tests, no network required
node app/sm2.test.js        # 12 scheduler tests
.venv/bin/python -m ingest  # rebuilds corpus/ from live sources
```

## The cutoff fence

The 2026 Bar tests law **as of 30 June 2025** (Bar Bulletin No. 1). Every
document carries a `promulgation_date`, and `config.COVERAGE_DATE` is the
single value that fences off anything later. Change that one value to sit a
different exam.

This is why parsers **refuse to guess** a date. A document with no reliable
date is dropped, not dated by assumption.

## Layout

| Path | Responsibility |
|---|---|
| `ingest/config.py` | Every tunable value |
| `ingest/schema.py` | What a document is, and what makes one invalid |
| `ingest/fetch.py` | Polite HTTP, TLS bundle, disk cache |
| `ingest/parse_lawphil.py` | lawphil HTML → Document |
| `ingest/parse_elibrary.py` | e-Library HTML → Document |
| `ingest/emit.py` | JSON shards + manifest + shrink check |
| `ingest/seeds.json` | What to ingest. Add URLs here as you study |
| `ingest/split.py` | Statutes → individual provisions (one per card) |
| `tests/fixtures/` | Real saved pages — read the README there first |
| `certs/` | The e-Library's missing TLS intermediate |
| `index.html` | The whole app UI. Four screens, no more |
| `app/sm2.js` | Spaced repetition. Pure functions, `node app/sm2.test.js` |
| `app/app.js` | Screens, storage, search |
| `sw.js` | Offline caching |

## How the corpus builds itself

`python -m ingest --cases --months=6 --per-month=8 --years=30`

Each run crawls the next six months not yet visited, newest first, taking at
most eight decisions per month. `corpus/crawl_state.json` records what is done
so runs continue rather than repeat — the first attempt lacked this and spent
its entire budget on three consecutive months of 1997.

The corpus is **additive**: `emit(merge=True)` adds to what is stored, so a
partial run can never discard what earlier runs downloaded. Fetched once, kept
forever.

A scheduled Action runs this every two hours from GitHub's IPs. The e-Library
throttles sustained crawling from one address, which is why bulk work does not
run from a laptop.

## Things that will bite you

**The e-Library serves an incomplete TLS chain.** `certs/elibrary-chain.pem`
supplies the intermediate it omits. Verification stays fully enabled. Never
"fix" a TLS error with `verify=False`. See `certs/README.md`. The intermediate
expires **2027-07-16**.

**lawphil states enactment dates last.** R.A. 386's body cites the 1866 Spanish
Civil Code before giving its own 1949 approval date. Taking the first date
found dates the Civil Code to 1866.

**e-Library decisions quote other cases' dates throughout.** Only the bracket
header — `[ G.R. No. 279692, June 11, 2025 ]` — is canonical.

**The shrink check will block a bad run.** If ingest produces materially fewer
documents than last time, it writes nothing and opens an issue. That is
correct behaviour: a broken scrape must never overwrite a good corpus.

## Adding documents

Append to `ingest/seeds.json`:

```json
{ "url": "...", "source": "lawphil" | "elibrary", "subject": "civil", "note": "..." }
```

Subjects match the official weights in `config.SUBJECT_WEIGHTS`: `remedial`
(25%), `civil` (20%), `commercial_tax` (20%), `political` (15%), `labor` (10%),
`criminal` (10%).

## Not yet built

The 1987 Constitution parses on neither parser (no R.A./Act number) and needs
its own. Bar question PDFs from `sc.judiciary.gov.ph` need a PDF path. Both are
deferred until a later phase needs them.

## Docs

- Design: `docs/superpowers/specs/2026-08-09-bar-review-app-design.md`
- Plan: `docs/superpowers/plans/2026-08-09-corpus-ingest.md`
