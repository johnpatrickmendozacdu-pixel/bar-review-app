---
name: verifying-legal-currency
description: Use when authoring, editing, or reviewing any legal content that will reach a student or practitioner - bar review questions, answer keys, legal explanations, or anything citing Philippine statutes and jurisprudence. Also use when a quote passes automated validation and you are about to ship it.
---

# Verifying Legal Currency

## Overview

A verbatim quote from a real document proves the text exists. It does not prove
the law is still in force, that you cited the provision that governs, or that
your conclusion follows from what you quoted.

**Passing the validator is not passing legal review.** The validator answers
"does this text exist in this document?" Every real defect shipped so far
answered that question correctly and was still wrong.

**Core rule: if you cannot verify a provision is current, do not ship the item.
Cite historical law when the question is historical, but never present
superseded law as the present rule.**

## When to Use

- Writing or editing any question, answer key, or legal explanation
- Reviewing content that already passed automated validation
- Adding a statute or case to the corpus
- Any time you are about to assert what the law *is*

Do not use for: non-legal content, or corpus plumbing that makes no legal claim.

## Source Precedence

**The Supreme Court e-Library is the primary legal basis. lawphil is a
secondary cross-reference.**

Every quotation must appear verbatim in the Court's own text. If the e-Library
copy of a document cannot be located, the item does not ship — fail closed.

The two sources transcribe the same statutes with small differences:
`wilfully` / `willfully`, `in manner` / `in a manner`, `benefit` / `benefits`.
These carry no legal weight and are tolerated automatically.

**Flag a divergence only when it changes the rule:** a different provision
number, an added or dropped qualifier, altered scope. The e-Library's copy of
PD 442 numbers the termination provision ART. 321 and reads "terminate an
employment *without a definite period*" — that is a substantive difference from
lawphil's Art. 282, and it stops the item.

The validator measures this automatically and rejects anything past the
threshold. When it does, read both texts before deciding — do not raise the
threshold.

## The Five Checks

Run all five on every item. A failure on any one means fix or delete — never
ship with a caveat.

### 1. Currency — is this still the law?

The corpus holds **original enacted texts**, not consolidated amended ones. A
1930 statute in the corpus reads as it did in 1930.

Before quoting any provision, ask: has this been amended, renumbered, or
repealed?

**Known live examples in this project:**

| Provision | Trap |
|---|---|
| RPC Art. 315 (estafa) | Peso thresholds amended by **RA 10951 (2017)**. Corpus shows 12,000/22,000 — superseded. |
| Labor Code Arts. 279, 282 | **Renumbered in 2015** to Arts. 294, 297 by DOLE Dept. Advisory 01-15. |
| Corporation Code (BP 68) | **Repealed and replaced** by RA 11232 (2019). |

If amended: cite the current provision. If the historical version matters to
the question, cite both and say which period each governs.

### 2. Completeness — did you cite the provision that actually governs?

The general rule is often displaced by a specific one. Quoting a true general
provision while a specific provision governs produces a confidently wrong
answer.

**Live example:** a sale of land in installments answered under Art. 1191
alone. Art. 1592 (rescission of sale of immovable requires judicial or notarial
demand) and RA 6552 (Maceda Law) govern. The Art. 1191 quote was verbatim and
the answer was still wrong.

Ask: is there a *lex specialis* for this subject matter, this object, this
party, or this transaction type?

### 3. Sufficiency — does the conclusion follow from the quote?

Every legal proposition asserted must be supported by a quoted authority in the
same item. If reaching the conclusion needs an unquoted premise, the item is
wrong-shaped.

**Live example:** Art. 19 quoted to ground a damages award. Art. 19 states a
standard of conduct; the action for damages arises under Art. 19 **in relation
to** Art. 20 or 21. The missing link made the answer unsupported.

### 4. Verifiability — is every cited source in the corpus?

If you name a statute or case, it must be in the corpus so the quote can be
checked and the link resolves. Naming an authority you cannot quote is exactly
the fabrication risk the whole system exists to prevent.

**Live example:** an item referenced BP 22, which is not in the corpus. That
limb was unverifiable and had to be deleted.

Either ingest the source, or remove the claim.

### 5. Conditionality — is a flat answer honest?

Where the law turns on facts, a forced yes/no is less accurate than the truth.
State the conditions: "Yes if X; no if Y" — with **every condition traceable to
a quoted authority**.

Conditionality is not hedging. Hedging is "this may vary, consult a reviewer."
Conditionality is "yes if the obligation is reciprocal; no if it is an
installment sale of personalty, where Art. 1484 governs."

## Historical Law

Old law and old cases are legitimate material. The rule is not "only cite
recent sources."

**Cite historical authority when:** the question is about the law at a past
time, the case remains the leading statement of a doctrine that has not
changed, or you are showing doctrinal development.

**Whenever you cite superseded authority, you MUST also cite what replaced it**
and mark which governs now. A student who memorises the old rule because you
did not flag the amendment has been actively harmed.

## Red Flags — STOP

- "It passed the validator, so it's accurate"
- "The quote is verbatim, so the answer is right"
- "This is well-known doctrine, I don't need to check the current text"
- "The amendment probably doesn't affect this part"
- "I'll note the amendment in a caveat and ship it"
- "Close enough for a practice question"
- "The general provision covers it"
- "I remember this provision" (you did not read it — go read it)

**All of these mean: run the five checks, or delete the item.**

## Rationalizations

| Excuse | Reality |
|---|---|
| "Mechanical validation passed" | It checks text existence, not legal force. Every defect so far passed it. |
| "It's only a practice question" | A student memorises practice answers. Wrong practice law becomes a wrong exam answer. |
| "The amendment is minor" | You cannot know that without reading the amendment. Read it. |
| "I'll flag it as possibly outdated" | A flagged wrong answer is still a wrong answer. Fix or delete. |
| "Deleting loses coverage" | Nine trustworthy items beat fourteen where five are wrong and unmarked. |
| "There's no time to verify each one" | Then author fewer. Volume is not the deliverable; accuracy is. |
| "The corpus is the official source" | The corpus holds *original* texts. Official ≠ current. |

## Quick Reference

Before shipping any item:

1. **Current?** Amended, renumbered, or repealed? Cite the current version.
2. **Complete?** Does a specific provision displace the general one you quoted?
3. **Sufficient?** Is every asserted proposition backed by a quote in this item?
4. **Verifiable?** Is every named source in the corpus?
5. **Conditional?** If the law turns on facts, do the conditions trace to quotes?

Any check fails → fix or delete. Never ship with a caveat.

## Common Mistakes

**Reviewing your own draft immediately.** You will read what you meant. Re-read
the provision text fresh from the corpus, then read your conclusion against it
as if someone else wrote it.

**Checking the quote instead of the law.** Confirming the words match the
document is check zero, not check one.

**Treating the date fence as a currency check.** The fence proves a document
predates the exam cutoff. A 1930 statute passes the fence and may still be
amended beyond recognition.
