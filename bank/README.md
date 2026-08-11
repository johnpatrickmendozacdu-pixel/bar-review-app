# Question bank

Scenario-based practice questions. Authored by hand (in Claude Code sessions),
validated mechanically, shipped as static JSON. There is no API key, no
generation service, and no runtime AI.

## The gate

`python -m bank` runs four checks per item. CI runs it on every push, so an
invalid bank cannot merge.

1. **Citations resolve.** Every `doc_id` exists in the corpus index.
2. **Quotes are verbatim.** Every `quote` appears as an exact substring of that
   document's corpus text, after whitespace normalisation. This is the check
   that makes fabricated authority impossible rather than unlikely.
3. **Date fence.** Every cited document is dated on or before 2025-06-30.
4. **Schema.** Type, subject, difficulty, question and answer key all valid.

A failing item is dropped and reported. It is never repaired automatically.

## Item shape

    {
      "id": "q-civil-0001",
      "schema_version": 1,
      "type": "hypothetical",
      "subject": "civil",
      "question": "Ana agreed to sell her lot to Ben ...",
      "answer_key": "Yes to both. The power to rescind ...",
      "authorities": [
        {
          "doc_id": "ra-386-art-1191",
          "citation": "Civil Code, Art. 1191",
          "quote": "The power to rescind obligations is implied in reciprocal ones",
          "source_url": "https://lawphil.net/..."
        }
      ],
      "difficulty": 2
    }

`type` is one of `hypothetical`, `issue_spotting`, `essay`, `doctrine`.
`subject` is one of `remedial`, `civil`, `commercial_tax`, `political`,
`labor`, `criminal`. `difficulty` is 1, 2 or 3.

## Authoring rules

- **Copy quotes, never retype them.** Read the text from `corpus/` and paste it.
  A remembered quote will fail check 2, which is the point.
- **Skip provisions not worth testing.** Repealing clauses, effectivity dates
  and definitions produce no question. Forcing an item out of every provision
  is what made the first version of this app useless.
- **The answer key explains; the quote proves.** Reasoning in `answer_key` is a
  study aid. Only the quoted text is authority, and the UI says so.
- **One question, one call.** State the facts, then ask something specific
  enough to have a defensible answer.

## Authoring workflow

Do not hand-write the mechanical fields. Scaffold them:

    python -m tools.scaffold --subject labor --count 8

This selects provisions that actually state a rule, picks a quote **already
verified against the e-Library and the corpus**, and fills in the citation and
source_url straight from the corpus so they cannot be typed wrong. It writes
`bank/drafts.json` (gitignored). Fill the TODO fields, drop `_provision_text`,
append to `questions.json`, and run `python -m bank`.

For questions built on decisions, brief the case first:

    python -m tools.brief gr-102858
    python -m tools.brief gr-102858 --search rescission

It marks each candidate sentence `[COURT]` or `[QUOTED]`. **Never quote a
`[QUOTED]` line as the Court's holding** — decisions quote parties, lower
courts and agencies constantly. In Director of Lands v. Abistado the line
"Neither one nor the other is dispensable" is a Ministry of Justice opinion,
not a holding.

## Adding items

Append to `questions.json`, then:

    python -m bank

Fix or delete anything reported before committing.
