# Answer Keys, Speed and Simplicity — Design

**Date:** 2026-08-11
**Status:** Approved
**Extends:** `2026-08-10-study-experience-design.md`

---

## 1. What this changes

Three things, in priority order:

1. **Answer keys carry real legal substance** — conditions, exceptions, and
   related cases with working links, not just one quoted provision.
2. **The app loads instantly and stays instant** as the corpus grows.
3. **Fewer screens, fewer choices**, understandable within five seconds.

Legal accuracy and consistency are the standing requirement, not a feature:
every answer key must be legally accurate, and accurate in the same way across
the whole bank.

## 2. Speed: the corpus leaves the browser

The app was fetching `corpus/provisions.json` (3.0 MB) on every first load,
alongside a `case.json` that had already reached 3.4 MB and would pass 40 MB
once the case crawl deepened. That is what made it feel slow, and it would only
get worse.

**The runtime does not need the corpus.** Each question already carries its own
verbatim quotes and source links — that is exactly what validation guarantees.
The corpus is a *build-time* asset used to author and verify questions.

| Asset | Before | Now |
|---|---|---|
| `bank/questions.json` | fetched | fetched — the only eager load |
| `corpus/provisions.json` | fetched eagerly (3.0 MB) | fetched only when Search is opened |
| `corpus/case.json` | precached by the service worker | never sent to the browser |

First paint therefore depends on question-bank size alone, and is unaffected by
corpus growth. Someone who only drills never downloads a provision.

The case crawl runs on GitHub's machines. The user never waits for it.

## 3. Item schema, version 2

```
{
  "id", "schema_version": 2, "type", "subject",
  "question",
  "answer_key",        // may be conditional; see §4
  "exceptions",        // carve-outs and qualifications; "" when genuinely none
  "authorities": [
    { "doc_id", "citation", "quote", "source_url", "role" }
  ],
  "difficulty"
}
```

`role` is `"controlling"` or `"related"`. Related cases are not a separate
array: they are authorities with a different role, so they pass through the
same validator and the same renderer. A related case therefore carries exactly
the same guarantee as a controlling one — a real corpus document, a verbatim
quote, and a link that resolves.

Every item must carry at least one `controlling` authority.

## 4. Answer keys may be conditional

A forced yes/no is often less accurate than the truth. Where the law turns on
facts, the answer key states the conditions:

> Yes, if the obligation is reciprocal and the breach is substantial. No, if
> the sale is of personal property payable in installments, where Art. 1484
> governs instead and the remedies are alternative.

**Rule: every condition stated must trace to a quoted authority in the same
item.** If reaching the conclusion needs an unquoted premise, the item is
wrong-shaped and must be rebuilt or dropped.

## 5. Accuracy: what is guaranteed, and what is not

**Mechanically guaranteed** by the validator, on every authority regardless of
role:

1. `doc_id` resolves in the corpus index
2. `quote` appears verbatim in that document's text (whitespace-normalised)
3. That document is dated on or before 2025-06-30
4. Schema complete; `role` valid; at least one `controlling` authority

This makes fabricated law impossible, not merely unlikely.

**Not mechanically guaranteed:** that the reasoning is legally correct. An item
can quote a provision perfectly and still draw a wrong conclusion. Legal
correctness is not a string operation, and no validator will ever catch it.

**Therefore, authoring discipline:**

- Nothing is asserted beyond what the quoted text supports.
- Where the law is conditional, the answer is conditional — with the conditions
  grounded in quoted text — rather than forced into yes/no.
- Exceptions are stated explicitly, because that is where exams live.
- Every item gets a second review pass, reading the provision text fresh
  against the written conclusion.
- Anything that cannot be grounded is deleted, not hedged.
- The authority sits next to the reasoning on screen, so the student can check
  the work in one glance instead of trusting it.

The residual risk is a subtly wrong conclusion drawn from correctly-quoted law.
This is stated plainly rather than hidden behind a green check.

## 6. Screens: five down to four

| Screen | Purpose |
|---|---|
| **Home** | One sentence of status, one big button, one quiet line of streak and accuracy |
| **Session** | One question. Think, reveal, self-grade, note |
| **Search the law** | Full-text search; loads provisions on first open only |
| **Settings** | Exam date, daily limit, subjects, backup |

**Deleted:** the separate progress screen (its numbers move inline to Home), the
session-finished screen (finishing returns Home with updated numbers), and the
collapsed subject picker (subjects become a plain visible row).

Home must be understandable in five seconds: status, button, nothing else above
the fold.

## 7. Answer key layout on screen

Fixed order, so the reader builds a rhythm:

1. **Answer** — the reasoning, conditional where the law is conditional
2. **Exceptions and qualifications** — omitted entirely when the field is empty
3. **Controlling authority** — citation, verbatim quote, link to the official source
4. **Related cases** — same shape, same guarantee

Authority blocks collapse on narrow screens so the key is not a wall of text on
a phone.

## 8. Responsive rules

Phone and laptop are equal targets.

- Single column that reflows; no horizontal scrolling at any width
- Minimum 48px tap targets; grade buttons stack below 380px
- Keyboard shortcuts on desktop (space reveals, 1/2/3 grade) — always an
  addition, never the only route
- Body text 17px minimum; legal prose serif at line-height 1.7
- Light and dark both correct

## 9. Corpus deepening

The e-Library has no usable search endpoint — its search is JavaScript-driven
and there is no form to post to. But the month index accepts any year, and
older months are far richer (March 1998: 86 decisions; June 2005: 166).

So: crawl broadly across history, then **search the local corpus** when
authoring to find cases genuinely on the doctrine at hand. Local search
replaces the remote search that does not exist.

Consequence: questions are authored around what the corpus contains. When no
good related case exists for a topic, the item ships with none rather than a
fabricated one.

## 10. Not being built

Live AI, API keys, accounts, servers, sync services, a progress screen, a
finished screen, and any runtime dependency beyond fetching static files.
