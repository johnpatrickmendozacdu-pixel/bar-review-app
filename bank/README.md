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

## Adding items

Append to `questions.json`, then:

    python -m bank

Fix or delete anything reported before committing.
