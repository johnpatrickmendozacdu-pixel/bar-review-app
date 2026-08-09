# Philippine Bar Review App — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** Personal 2026 Bar review tool, single user, optional sharing with friends.

---

## 1. Problem

A Philippine law student preparing for the 2026 Bar needs a review tool that is
free, always available, and legally trustworthy. Existing options are either
paid research platforms or generic AI chat that fabricates citations.

The 2026 Bar Examinations (per Bar Bulletin No. 1, 16 October 2025, under
A.M. 24-10-05-SC) are:

- **3 days**, localized and digitalized, held 6, 9 and 13 September 2026.
- **6 subjects**, weighted: Remedial Law + Legal & Judicial Ethics + Practical
  Exercises (25%), Civil Law + Land Titles and Deeds (20%), Commercial and
  Taxation Laws (20%), Political and Public International Law (15%), Labor Law
  and Social Legislation (10%), Criminal Law (10%).
- **20 essay questions per subject. No multiple choice.**
- Coverage limited to **laws, rules, issuances and jurisprudence as of
  30 June 2025**.

Two consequences drive the whole design: practice must be **essay-first**, and
the corpus must be **date-fenced** at 30 June 2025.

## 2. Guardrails and what they actually mean

| Stated requirement | Honest reading |
|---|---|
| 100% accurate | Achievable for **retrieval and citations**, enforced by a validator. A grader's judgment on an essay is an opinion and is labelled as such in the UI. |
| 100% free | $0 hosting (GitHub Pages), $0 CI (GitHub Actions), $0 AI (Gemini free tier, user-supplied key). |
| 100% functional / "not break" | No build step, no server, no runtime dependencies. Last-good corpus always serves. Every feature degrades rather than failing. |
| 100% secure | No server to breach. `drive.file` OAuth scope only. Strict CSP. No third-party scripts. Free-tier-only key. Not "unhackable" — small attack surface. |
| Local only | IndexedDB is the source of truth. Google Drive is an opt-in mirror in an app-created folder. |
| Auto-updates | Scheduled GitHub Action re-ingests and commits the corpus. |

**Non-goal:** legal advice. This is a study tool. The AI never states law from
its own parametric memory.

## 3. Architecture

Three layers.

### 3.1 Corpus — build time, GitHub Actions

A Python ingest script runs on a schedule on GitHub's runners (never required
on the user's machine).

Sources:

- **lawphil.net** — statutes and Republic Acts named in the official 2026 Bar
  syllabus. (Same source `roelchristian/lexsearch` uses.)
- **elibrary.judiciary.gov.ph** — jurisprudence cited in the syllabus, plus
  cases fetched on demand.
- **sc.judiciary.gov.ph** — past Bar examination question PDFs (2023, 2024,
  2025 confirmed published).

Ingest is **syllabus-driven and on demand**: seed from the syllabus, then fetch
lazily as questions or searches touch new documents, caching permanently. The
corpus stays small and relevant instead of mirroring decades of case law.

Document schema:

```
{ id, schema_version, type, title, citation, promulgation_date, source_url, text }
```

Output: static JSON shards plus a search index, committed to the repo.

**Robustness requirements:**

- The e-Library presents an incomplete TLS certificate chain. Handle with an
  explicit, documented, pinned CA bundle. **Never** a blanket
  `verify=False`.
- Polite rate limiting against government servers.
- **Shrink check:** a run producing materially fewer documents than the last
  good run must refuse to commit and open a GitHub issue. Silent corpus
  corruption is the worst failure mode; loud failure is required.

### 3.2 App — static PWA, GitHub Pages

Vanilla HTML, CSS and JavaScript. No framework, no bundler, no `npm install`.
Native elements throughout (`<details>` for reveal-answer, `<dialog>` for
modals, plain form controls) — familiar behavior is what makes it usable
without instruction.

A service worker caches corpus shards, so the app works fully offline after
first visit.

### 3.3 AI — user's key, user's browser

Direct Gemini calls from the client, using a key the user pastes into
Settings, stored locally.

Every prompt is **closed-book**:

1. Retrieve relevant corpus documents (date-fenced).
2. Pass their text into the prompt.
3. Instruct the model: *if the answer is not in the provided text, say you
   cannot answer.*
4. **Validate every returned citation against the local index.** Citations
   that do not resolve to a real document ID are stripped and flagged.

Step 4 is the accuracy guarantee. The prompt is a request; the validator is
enforcement.

## 4. The cutoff fence

A single setting, `coverage_date = 2025-06-30`.

Retrieval filters every document by `promulgation_date` **before** anything
reaches a prompt. Post-cutoff law cannot contaminate an answer key. Sitting a
later exam means changing one value.

## 5. Screens

Four. No more.

1. **Home** — one button, *Start today's review*. Below it, quiet text: what is
   due, days until the exam. Below that, a small *pick something else* link
   revealing the four modes.
2. **Session** — one question at a time, full width, nothing else on screen.
   Answer, then reveal.
3. **Library** — search box, results, full document text.
4. **Settings** — API key, exam date, export and sync.

## 6. Study modes

Each mode is one file exposing a common `run(session)` interface.

- **Drills** (`drills.js`) — SM-2 spaced repetition over doctrine cards
  (elements, periods, exceptions). No AI calls, fully offline. Cards are
  generated at ingest from statutory provisions and **each requires one-time
  user confirmation before entering rotation** — otherwise the user is
  trusting the model after all.
- **Essay** (`essay.js`) — hypothetical, typed answer, then grading against an
  ALAC rubric (Answer, Law, Application, Conclusion) using retrieved
  authority. Every point of feedback quotes the provision or case it rests on.
  Feedback with no citation attached is a bug.
- **Mock exam** (`mock.js`) — 20 essays, timed, one subject, bulk-graded after.
- **Ask** (`ask.js`) — plain-language question, answer assembled only from
  retrieved documents, every citation clickable to full text.

### Queue logic

Due spaced-repetition cards first — that is the retention engine and is not
negotiable. Once due cards clear, serve essays from the subject with the lowest
recent scores, weighted by official exam percentages. Simple and explainable;
no black box.

## 7. Data and sync

- **IndexedDB** is the source of truth: essays, grades, SM-2 schedule, notes.
- **Google Drive** is an opt-in mirror. OAuth 2.0 with PKCE, browser-only, no
  client secret (a static app has none to leak).
- **Scope: `drive.file` only.** The app can touch only files it created. A full
  compromise still cannot reach the rest of the user's Drive. Full-Drive scope
  is never requested. *Confirm Google's current scope classification and
  unverified-app test-user cap at build time — these change, and the cap
  matters if friends use the app.*
- Manual JSON export to the app folder always available.

**Security posture:** strict Content-Security-Policy; zero third-party scripts
or CDN tags; AI output never rendered as raw HTML; free-tier-only API key with
no billing attached, so the worst case is stolen quota, not a bill. Residual
risks are the user's GitHub account (enable 2FA), dependencies (kept near-zero
and pinned) and their own machine.

## 8. Failure behavior

| Failure | Behavior |
|---|---|
| No internet | Drills and full-text search still work. |
| AI quota exhausted or API down | App says so plainly, offers drills. |
| Scraper broken | Last good corpus keeps serving; issue opened. |
| Retrieval finds nothing solid | *"I can't ground this one."* Never a guess. |

AI is a feature, never a dependency.

## 9. Designed for iteration

- One file per mode behind `run(session)`. Add or remove a mode by adding or
  removing one file and one registration line.
- Corpus shards carry `schema_version`; the app refuses an unknown version
  rather than silently misreading it.
- Every tunable in one `config.js`: cutoff date, subject weights, SM-2
  constants, model name, exam date.

No plugin system, no abstraction layer. Three conventions are enough.

## 10. Build order

1. Corpus ingest
2. Drills
3. Library search
4. Essay grading
5. Mock exams

Drills come before any AI feature because they require none and will
immediately reveal whether the corpus is any good. Each phase should be used
for a week before the next begins.

## 11. Known limitations

- Official *suggested answers* are not reliably published by the Supreme Court;
  well-known compilations come from UP Law Center and private reviewers, which
  is a licensing question rather than a scraping one. Answer keys are therefore
  derived from primary authority in the corpus, not from copied model answers.
- Essay grading quality is bounded by the free-tier model.
- On-demand case fetching arrives on the next ingest run, not instantly,
  because a browser cannot scrape cross-origin.

## References

- Bar Bulletin No. 1 (16 Oct 2025) — https://sc.judiciary.gov.ph/wp-content/uploads/2025/10/2026-BAR-Bar-Bulletin-No.-1-October-16-2025.pdf
- SC e-Library — https://elibrary.judiciary.gov.ph/
- `roelchristian/lexsearch` — lawphil scraping precedent
- `llegomark/betterlegal` — PH legal AI precedent, streaming + rate limiting
