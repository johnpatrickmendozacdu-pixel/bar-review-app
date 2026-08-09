# HTML fixtures

Real pages, saved verbatim. Parser tests run against these, so the suite never
touches the network and never depends on a government server being up.

| Fixture | Source URL | Captured |
|---|---|---|
| `lawphil_ra386.html` | https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html | 2026-08-09 |
| `elibrary_case.html` | https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/70158 | 2026-08-09 |
| `elibrary_month.html` | https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/Jun/2025/1 | 2026-08-09 |

## What the real markup taught us

Both facts below were **discovered from these fixtures** and contradict the
obvious implementation. Do not "simplify" the parsers back.

**lawphil puts the enactment date last.** R.A. 386's body cites the 1866
Spanish Civil Code repeatedly before stating `Approved: June 18, 1949` at the
very end. A parser that takes the first date it sees dates the Civil Code to
**1866** — silently poisoning the cutoff fence. `parse_lawphil` looks for
`Approved:` first and falls back to the *last* date, never the first.

**The e-Library has a canonical header line:** `[ G.R. No. 279692, June 11,
2025 ]` — docket and promulgation date together. Decisions quote other cases
and their dates throughout the body, so scanning the body is unreliable.
`parse_elibrary` requires this header and **refuses to guess** a date rather
than risk a wrong one.

## Useful e-Library URL patterns

| Pattern | What it lists |
|---|---|
| `/thebookshelf/docmonth/<Mon>/<YYYY>/1` | All decisions promulgated that month |
| `/thebookshelf/showdocs/1/<id>` | A single decision |
| `/thebookshelf/2` | Republic Acts |
| `/thebookshelf/11` | Rules of Court |
| `/thebookshelf/3` | Constitutions |

The date-indexed month listing is what makes the 30 June 2025 cutoff cheap to
enforce: we can enumerate by month and simply stop at the boundary.

## Refreshing

When a parser breaks in production but passes locally, the site markup changed.

    python -m tools.capture_fixture <url> <name>

Then fix the parser until tests pass against the NEW fixture. The fixture is
the truth; the parser is the guess.
