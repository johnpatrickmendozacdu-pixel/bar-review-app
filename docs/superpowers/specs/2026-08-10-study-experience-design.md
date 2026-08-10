# Study Experience Redesign — Design

**Date:** 2026-08-10
**Status:** Approved
**Supersedes:** the drill design in `2026-08-09-bar-review-app-design.md` §6 (Drills)

---

## 1. Why this exists

Phase 2 shipped spaced-repetition cards where each card was one statutory
provision: front = citation, back = verbatim text. It was accurate and
useless. Three failures:

**Wrong unit.** One card per article gave Civil Code Art. 1 ("This Act shall
be known as the Civil Code") the same weight as Art. 1191. Most of 2,270
articles are definitions, effectivity clauses, and repealing provisions that
nobody studies in isolation.

**Wrong direction.** Front "Art. 19" → back "the text" trains *recognition*.
The Bar tests *application*: given facts, which rule governs and why. Only one
of those skills was being drilled.

**No context, no notes.** Provisions floated alone — no related articles, no
case applying them, nowhere to record what a professor said.

The visual design was also bare, but restyling alone would have produced a
prettier app that still taught nothing.

## 2. What changes

Study items become **scenario-based questions that challenge legal thinking**,
each with a revealed answer key whose reasoning is grounded in the Supreme
Court e-Library and lawphil corpus.

## 3. Guardrails, and how each is met

| Requirement | How |
|---|---|
| 100% free | Static site, static content. No API key, no secret, no quota, no paid tier. |
| 100% functional | No runtime network dependency. Works offline after first load. |
| 100% secure | No key to steal, no auth, no server, no runtime AI call. |
| 100% accurate | Four-check validation gate (§5). Anything failing is discarded, never shipped. |
| Local only | Progress, notes, and scores in browser storage. Manual export. |
| Usable by a non-technical 50-year-old | §8. |

**No runtime AI anywhere.** No live grading, no live generation, no API key
for anyone — not the author, not the user, not friends.

## 4. Where questions come from

Question items are **authored in Claude Code sessions against the local
corpus** and committed as static JSON. There is no scheduled LLM job and no
API key stored anywhere.

The author reads corpus documents directly, writes items grounded in them, and
runs the validator before commit. The bank grows on demand — "write 100 more
Remedial Law questions" — rather than on a cron. This is deliberate: batches
can be aimed at weak subjects, and every batch gets reviewed.

**Generated reasoning is a study aid, not authority.** The verbatim law quoted
beside it is the authority. The UI states this distinction plainly rather than
blurring it.

**The generator may skip.** Provisions not worth testing — repealing clauses,
definitions, effectivity dates — produce no item. Forcing a question out of
every provision is what created the original problem.

## 5. The validation gate

Every item passes all four checks or is discarded and logged. Answer keys carry
the same gate as questions.

1. **Citations resolve.** Every cited document id exists in the corpus index.
2. **Quotes are verbatim.** Every quoted passage appears as an exact substring
   of the cited document's corpus text. This catches invented quotations
   outright and is the strongest single check in the system.
3. **Date fence.** Every cited document has `promulgation_date` on or before
   2025-06-30, the 2026 Bar coverage cut-off.
4. **Schema.** Required fields present and non-empty; `type` known; `subject`
   one of the six official subjects.

Validation runs in CI, so a malformed bank cannot merge.

## 6. Item types

One session mixes types. All four are self-graded — the user compares their
own reasoning against the answer key and the quoted authority.

| Type | Shape | Time |
|---|---|---|
| `hypothetical` | 3–5 sentence fact pattern, specific question | 2–4 min |
| `issue_spotting` | Longer facts, several buried issues, list them | 5–8 min |
| `essay` | Full bar-style question, typed ALAC answer, compare to model answer | 15–30 min |
| `doctrine` | Elements, periods, exceptions — warm-up layer | under 1 min |

### Item schema

```
{
  id, schema_version, type, subject,
  question,            // the fact pattern and the call
  answer_key,          // the reasoning — labelled a study aid in the UI
  authorities: [       // every one validated per §5
    { doc_id, citation, quote, source_url }
  ],
  difficulty           // 1-3, drives ordering
}
```

## 7. Self-grading and progress

After revealing the key the user answers one question: **No / Partly / Yes**.
That grade drives both spaced repetition and the score history.

Tracked locally: per-item outcome and timestamp, accuracy overall and per
subject, session history, current streak, weakest subjects. Weakest subject
surfaces first in the queue after due items clear, weighted by the official
exam percentages (Remedial 25%, Civil 20%, Commercial/Tax 20%, Political 15%,
Labor 10%, Criminal 10%).

## 8. Interface

Four screens. One primary action each.

1. **Home** — one button, *Start today's review*. Below it: what's due, accuracy
   this week, days to the exam.
2. **Session** — one question, full width. Think, reveal, self-grade, note.
3. **Library** — search the law, read full text, attach notes.
4. **Progress** — accuracy over time, by subject, session history.

Notes attach to any question, provision, or case. Searchable. Included in
backup export.

### Readability rules

Non-negotiable, because the reader is 50, non-technical, and reading for hours:

- Body text 17px minimum; legal prose in serif, UI chrome in sans
- Line height 1.7 on legal text; measure capped around 70 characters
- No icon without a text label
- No hover-only affordances, no gestures, no hidden menus
- One primary action per screen; destructive actions confirm
- Full light and dark support
- Every interactive element keyboard reachable, visible focus ring

## 9. Prerequisite: the case corpus

Grounded reasoning needs cases to ground in. The corpus currently holds **one**
decision. Before question authoring begins, ingest e-Library decisions up to
2025-06-30 using the month index (`/thebookshelf/docmonth/<Mon>/<YYYY>/1`),
tagged by subject.

Volume target: enough leading cases per subject to support real questions, not
a full mirror of the e-Library. Politeness limits from the Phase 1 fetcher
apply unchanged.

## 10. Build order

1. **Case corpus expansion** — month-index crawler, subject tagging, date fence
2. **Question bank** — validator first, then authored items, CI-enforced
3. **App rebuild** — session flow, self-grading, notes, progress, readability

Each stage produces something usable on its own.

## 11. Known limitations

- The bank grows on demand, not on a schedule. First release is a few hundred
  items, not thousands.
- Answer-key *reasoning* is authored, not judicially endorsed. Only the quoted
  provisions and case passages are authority, and the UI says so.
- Essay practice has no automated feedback by design. The user self-grades
  against the model answer and the controlling authority.
- Subject tagging of cases is heuristic and will misfile some decisions.

## 12. What is deliberately not built

Live AI grading, in-browser generation, API keys, accounts, servers, sync
services, and any runtime network dependency beyond fetching static files.
