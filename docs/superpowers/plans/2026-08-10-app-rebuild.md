# App Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace provision flashcards with a scenario-question study session that a non-technical 50-year-old can use for hours — self-graded, with notes, progress, and readable legal typography.

**Architecture:** Same static no-build stack. `sm2.js` is unchanged and stays the scheduler. New modules split by responsibility: `store.js` owns persistence, `session.js` owns the study loop, `progress.js` owns statistics, `render.js` owns DOM. `app.js` shrinks to wiring.

**Tech Stack:** Vanilla HTML/CSS/JS, ES modules, no framework, no bundler, no dependencies. Tests via `node --test`.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-10-study-experience-design.md`:

- **No runtime AI anywhere.** No live grading, no live generation, no API key for anyone.
- **Local only.** Progress, notes, and scores in browser storage. Manual export.
- Body text **17px minimum**; legal prose in serif, UI chrome in sans.
- Line height **1.7** on legal text; measure capped around **70 characters**.
- **No icon without a text label.**
- **No hover-only affordances, no gestures, no hidden menus.**
- One primary action per screen; destructive actions confirm.
- Full light and dark support.
- Every interactive element keyboard reachable, with a visible focus ring.
- Self-grading is **No / Partly / Yes**.
- Generated reasoning is a **study aid, not authority** — the UI must say so.

---

## File Structure

| File | Responsibility |
|---|---|
| `app/sm2.js` | Unchanged. Spaced repetition maths |
| `app/store.js` | localStorage: cards, notes, settings, session history. All persistence |
| `app/session.js` | Study loop: build queue, current item, grading. No DOM |
| `app/progress.js` | Statistics from history: accuracy, streak, per-subject |
| `app/render.js` | DOM rendering for each screen. No business logic |
| `app/app.js` | Wiring and event handlers only |
| `app/style.css` | Rewritten for readability rules |
| `index.html` | Five screens |
| `app/store.test.js` | node tests |
| `app/session.test.js` | node tests |
| `app/progress.test.js` | node tests |

---

### Task 1: Storage layer

**Files:**
- Create: `app/store.js`
- Test: `app/store.test.js`

**Interfaces:**
- Consumes: nothing
- Produces (all take an injected storage object so tests need no browser):
  - `createStore(storage)` returning an object with:
    - `getCards() -> object`, `setCard(card) -> void`
    - `getNote(refId) -> string`, `setNote(refId, text) -> void`, `allNotes() -> object`
    - `getSettings() -> object`, `setSettings(partial) -> void`
    - `appendHistory(entry) -> void`, `getHistory() -> array`
    - `exportAll() -> object`, `importAll(data) -> void`
  - `DEFAULT_SETTINGS`

History entry shape: `{ itemId, subject, grade, at }` where `grade` is `"no" | "partly" | "yes"` and `at` is epoch ms.

- [ ] **Step 1: Write the failing test**

Create `app/store.test.js`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_SETTINGS, createStore } from "./store.js";

function fakeStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
    removeItem: (k) => data.delete(k),
  };
}

test("cards round-trip", () => {
  const store = createStore(fakeStorage());
  store.setCard({ id: "q-1", reps: 1, ease: 2.5, interval: 1, due: 0, lapses: 0 });
  assert.equal(store.getCards()["q-1"].reps, 1);
});

test("an empty store returns sane defaults", () => {
  const store = createStore(fakeStorage());
  assert.deepEqual(store.getCards(), {});
  assert.deepEqual(store.getHistory(), []);
  assert.equal(store.getSettings().newLimit, DEFAULT_SETTINGS.newLimit);
});

test("corrupt json does not throw", () => {
  const storage = fakeStorage();
  storage.setItem("barrev.cards", "{not json");
  const store = createStore(storage);
  assert.deepEqual(store.getCards(), {});
});

test("notes round-trip and are keyed by reference id", () => {
  const store = createStore(fakeStorage());
  store.setNote("ra-386-art-1191", "Prof: this is resolution, not 1381 rescission");
  assert.match(store.getNote("ra-386-art-1191"), /resolution/);
  assert.equal(store.getNote("nothing-here"), "");
});

test("an empty note is removed rather than stored", () => {
  const store = createStore(fakeStorage());
  store.setNote("x", "temp");
  store.setNote("x", "   ");
  assert.equal(Object.keys(store.allNotes()).length, 0);
});

test("settings merge rather than replace", () => {
  const store = createStore(fakeStorage());
  store.setSettings({ newLimit: 5 });
  assert.equal(store.getSettings().newLimit, 5);
  assert.equal(store.getSettings().examDate, DEFAULT_SETTINGS.examDate);
});

test("history appends in order", () => {
  const store = createStore(fakeStorage());
  store.appendHistory({ itemId: "q-1", subject: "civil", grade: "yes", at: 1 });
  store.appendHistory({ itemId: "q-2", subject: "civil", grade: "no", at: 2 });
  assert.deepEqual(store.getHistory().map((h) => h.itemId), ["q-1", "q-2"]);
});

test("export then import restores everything", () => {
  const a = createStore(fakeStorage());
  a.setCard({ id: "q-1", reps: 3, ease: 2.5, interval: 6, due: 0, lapses: 0 });
  a.setNote("ra-386-art-1191", "note text");
  a.appendHistory({ itemId: "q-1", subject: "civil", grade: "yes", at: 1 });
  a.setSettings({ newLimit: 7 });

  const b = createStore(fakeStorage());
  b.importAll(a.exportAll());

  assert.equal(b.getCards()["q-1"].reps, 3);
  assert.equal(b.getNote("ra-386-art-1191"), "note text");
  assert.equal(b.getHistory().length, 1);
  assert.equal(b.getSettings().newLimit, 7);
});

test("importing junk throws rather than wiping good data", () => {
  const store = createStore(fakeStorage());
  store.setCard({ id: "q-1", reps: 1, ease: 2.5, interval: 1, due: 0, lapses: 0 });
  assert.throws(() => store.importAll({ nonsense: true }));
  assert.equal(Object.keys(store.getCards()).length, 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test app/store.test.js`
Expected: FAIL — cannot find module `./store.js`

- [ ] **Step 3: Write the store**

Create `app/store.js`:

```javascript
// All persistence lives here. Storage is injected so this is testable in node
// and swappable if localStorage is ever outgrown.
// ponytail: localStorage. Progress is kilobytes; move to IndexedDB only if it
// approaches the ~5MB cap.

const KEYS = {
  cards: "barrev.cards",
  notes: "barrev.notes",
  settings: "barrev.settings",
  history: "barrev.history",
};

export const DEFAULT_SETTINGS = {
  examDate: "2026-09-06",
  newLimit: 20,
  subjects: ["civil", "criminal", "political", "commercial_tax", "labor", "remedial"],
};

function readJson(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

export function createStore(storage) {
  const write = (key, value) => storage.setItem(key, JSON.stringify(value));

  return {
    getCards: () => readJson(storage, KEYS.cards, {}),

    setCard(card) {
      const cards = this.getCards();
      cards[card.id] = card;
      write(KEYS.cards, cards);
    },

    allNotes: () => readJson(storage, KEYS.notes, {}),

    getNote(refId) {
      return this.allNotes()[refId] || "";
    },

    setNote(refId, text) {
      const notes = this.allNotes();
      if (!text || !text.trim()) delete notes[refId];
      else notes[refId] = text;
      write(KEYS.notes, notes);
    },

    getSettings: () => ({
      ...DEFAULT_SETTINGS,
      ...readJson(storage, KEYS.settings, {}),
    }),

    setSettings(partial) {
      write(KEYS.settings, { ...this.getSettings(), ...partial });
    },

    getHistory: () => readJson(storage, KEYS.history, []),

    appendHistory(entry) {
      const history = this.getHistory();
      history.push(entry);
      write(KEYS.history, history);
    },

    exportAll() {
      return {
        version: 1,
        cards: this.getCards(),
        notes: this.allNotes(),
        settings: this.getSettings(),
        history: this.getHistory(),
      };
    },

    importAll(data) {
      if (!data || typeof data !== "object" || !data.cards || typeof data.cards !== "object") {
        throw new Error("That file is not a Bar Review backup.");
      }
      write(KEYS.cards, data.cards);
      write(KEYS.notes, data.notes || {});
      write(KEYS.settings, { ...DEFAULT_SETTINGS, ...(data.settings || {}) });
      write(KEYS.history, Array.isArray(data.history) ? data.history : []);
    },
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test app/store.test.js`
Expected: PASS — 9 tests

- [ ] **Step 5: Commit**

```bash
git add app/store.js app/store.test.js
git commit -m "feat: add storage layer for cards, notes, settings and history"
```

---

### Task 2: Session logic

**Files:**
- Create: `app/session.js`
- Test: `app/session.test.js`

**Interfaces:**
- Consumes: `newCard`, `review`, `buildQueue`, `AGAIN`, `HARD`, `GOOD` from `./sm2.js`
- Produces:
  - `GRADE_QUALITY = { no: AGAIN, partly: HARD, yes: GOOD }`
  - `startSession({ items, cards, settings, subject, now }) -> { queue }` — queue is an array of item objects
  - `gradeItem({ item, card, grade, now }) -> { card, historyEntry }`

Items are bank items: `{ id, type, subject, question, answer_key, authorities, difficulty }`.

- [ ] **Step 1: Write the failing test**

Create `app/session.test.js`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { newCard } from "./sm2.js";
import { GRADE_QUALITY, gradeItem, startSession } from "./session.js";

const T0 = 1000000000000;

const ITEMS = [
  { id: "q-civil-1", type: "hypothetical", subject: "civil", question: "a", answer_key: "b", authorities: [], difficulty: 1 },
  { id: "q-civil-2", type: "doctrine", subject: "civil", question: "a", answer_key: "b", authorities: [], difficulty: 2 },
  { id: "q-crim-1", type: "hypothetical", subject: "criminal", question: "a", answer_key: "b", authorities: [], difficulty: 1 },
];

const SETTINGS = { newLimit: 20, subjects: ["civil", "criminal"] };

test("a session includes only enabled subjects", () => {
  const { queue } = startSession({
    items: ITEMS,
    cards: {},
    settings: { ...SETTINGS, subjects: ["civil"] },
    subject: null,
    now: T0,
  });
  assert.ok(queue.every((i) => i.subject === "civil"));
  assert.equal(queue.length, 2);
});

test("choosing a subject overrides the enabled list", () => {
  const { queue } = startSession({
    items: ITEMS,
    cards: {},
    settings: SETTINGS,
    subject: "criminal",
    now: T0,
  });
  assert.equal(queue.length, 1);
  assert.equal(queue[0].subject, "criminal");
});

test("the new-card limit caps the queue", () => {
  const { queue } = startSession({
    items: ITEMS,
    cards: {},
    settings: { ...SETTINGS, newLimit: 1 },
    subject: null,
    now: T0,
  });
  assert.equal(queue.length, 1);
});

test("due items come before unseen ones", () => {
  const cards = {
    "q-crim-1": { ...newCard("q-crim-1"), reps: 2, interval: 1, due: T0 - 1000 },
  };
  const { queue } = startSession({ items: ITEMS, cards, settings: SETTINGS, subject: null, now: T0 });
  assert.equal(queue[0].id, "q-crim-1");
});

test("an empty queue is returned rather than throwing", () => {
  const { queue } = startSession({
    items: [],
    cards: {},
    settings: SETTINGS,
    subject: null,
    now: T0,
  });
  assert.deepEqual(queue, []);
});

test("grading yes schedules the card forward", () => {
  const item = ITEMS[0];
  const { card } = gradeItem({ item, card: newCard(item.id), grade: "yes", now: T0 });
  assert.equal(card.reps, 1);
  assert.ok(card.due > T0);
});

test("grading no resets the card and keeps it due now", () => {
  const item = ITEMS[0];
  let card = gradeItem({ item, card: newCard(item.id), grade: "yes", now: T0 }).card;
  card = gradeItem({ item, card, grade: "no", now: T0 }).card;
  assert.equal(card.reps, 0);
  assert.equal(card.due, T0);
  assert.equal(card.lapses, 1);
});

test("partly advances but more slowly than yes", () => {
  const item = ITEMS[0];
  const partly = gradeItem({ item, card: newCard(item.id), grade: "partly", now: T0 }).card;
  const yes = gradeItem({ item, card: newCard(item.id), grade: "yes", now: T0 }).card;
  assert.ok(partly.ease < yes.ease);
  assert.equal(partly.reps, 1);
});

test("grading produces a history entry carrying the subject", () => {
  const item = ITEMS[0];
  const { historyEntry } = gradeItem({ item, card: newCard(item.id), grade: "yes", now: T0 });
  assert.deepEqual(historyEntry, { itemId: "q-civil-1", subject: "civil", grade: "yes", at: T0 });
});

test("every grade name maps to an sm2 quality", () => {
  assert.deepEqual(Object.keys(GRADE_QUALITY).sort(), ["no", "partly", "yes"]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test app/session.test.js`
Expected: FAIL — cannot find module `./session.js`

- [ ] **Step 3: Write session logic**

Create `app/session.js`:

```javascript
// The study loop. No DOM, no storage — just what to show next and what a
// grade does.

import { AGAIN, GOOD, HARD, buildQueue, newCard } from "./sm2.js";

// Three self-grades, mapped onto SM-2's quality scale. A tired student at 11pm
// should not be grading themselves on a six-point scale.
export const GRADE_QUALITY = { no: AGAIN, partly: HARD, yes: GOOD };

export function startSession({ items, cards, settings, subject, now }) {
  const pool = subject
    ? items.filter((i) => i.subject === subject)
    : items.filter((i) => settings.subjects.includes(i.subject));

  const states = pool.map((i) => cards[i.id] || newCard(i.id));
  const ordered = buildQueue(states, now, settings.newLimit);

  const byId = new Map(pool.map((i) => [i.id, i]));
  return { queue: ordered.map((c) => byId.get(c.id)).filter(Boolean) };
}

export function gradeItem({ item, card, grade, now }) {
  const quality = GRADE_QUALITY[grade];
  if (quality === undefined) throw new Error(`unknown grade: ${grade}`);

  return {
    card: reviewCard(card, quality, now),
    historyEntry: { itemId: item.id, subject: item.subject, grade, at: now },
  };
}

function reviewCard(card, quality, now) {
  // Imported separately so the mapping above stays readable.
  return review(card, quality, now);
}

import { review } from "./sm2.js";
```

Note: move the `import { review }` line to the top with the other imports —
ES modules hoist imports, but keeping them together is clearer. The final
import block should be:

```javascript
import { AGAIN, GOOD, HARD, buildQueue, newCard, review } from "./sm2.js";
```

and the trailing import line deleted.

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test app/session.test.js`
Expected: PASS — 10 tests

- [ ] **Step 5: Commit**

```bash
git add app/session.js app/session.test.js
git commit -m "feat: add session queue and self-grading logic"
```

---

### Task 3: Progress statistics

**Files:**
- Create: `app/progress.js`
- Test: `app/progress.test.js`

**Interfaces:**
- Consumes: history entries `{ itemId, subject, grade, at }`
- Produces:
  - `accuracy(history) -> number` — percentage 0-100, `yes` counts full, `partly` counts half
  - `accuracyBySubject(history) -> object` — subject to percentage
  - `weakestSubject(history, minimum) -> string | null`
  - `streakDays(history, now) -> number`
  - `sessionsByDay(history) -> array` of `{ day, count, accuracy }`, oldest first
  - `daysUntil(examDate, now) -> number`

- [ ] **Step 1: Write the failing test**

Create `app/progress.test.js`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import {
  accuracy,
  accuracyBySubject,
  daysUntil,
  sessionsByDay,
  streakDays,
  weakestSubject,
} from "./progress.js";

const DAY = 86400000;
const NOW = Date.parse("2026-08-10T09:00:00Z");

const h = (subject, grade, at) => ({ itemId: "x", subject, grade, at });

test("accuracy counts yes as full and partly as half", () => {
  const history = [h("civil", "yes", NOW), h("civil", "partly", NOW), h("civil", "no", NOW)];
  assert.equal(accuracy(history), 50);
});

test("accuracy of an empty history is zero, not NaN", () => {
  assert.equal(accuracy([]), 0);
});

test("accuracy is rounded to a whole number", () => {
  const history = [h("civil", "yes", NOW), h("civil", "no", NOW), h("civil", "no", NOW)];
  assert.equal(accuracy(history), 33);
});

test("accuracy splits by subject", () => {
  const history = [
    h("civil", "yes", NOW),
    h("civil", "yes", NOW),
    h("criminal", "no", NOW),
  ];
  const bySubject = accuracyBySubject(history);
  assert.equal(bySubject.civil, 100);
  assert.equal(bySubject.criminal, 0);
});

test("the weakest subject is the lowest scorer with enough attempts", () => {
  const history = [
    h("civil", "yes", NOW),
    h("civil", "yes", NOW),
    h("criminal", "no", NOW),
    h("criminal", "no", NOW),
  ];
  assert.equal(weakestSubject(history, 2), "criminal");
});

test("a subject below the attempt minimum is not called weakest", () => {
  const history = [h("civil", "yes", NOW), h("civil", "yes", NOW), h("labor", "no", NOW)];
  assert.equal(weakestSubject(history, 2), "civil");
});

test("weakest subject of an empty history is null", () => {
  assert.equal(weakestSubject([], 2), null);
});

test("a streak counts consecutive days ending today", () => {
  const history = [h("civil", "yes", NOW - 2 * DAY), h("civil", "yes", NOW - DAY), h("civil", "yes", NOW)];
  assert.equal(streakDays(history, NOW), 3);
});

test("a gap breaks the streak", () => {
  const history = [h("civil", "yes", NOW - 5 * DAY), h("civil", "yes", NOW)];
  assert.equal(streakDays(history, NOW), 1);
});

test("studying yesterday but not today keeps the streak alive", () => {
  const history = [h("civil", "yes", NOW - DAY)];
  assert.equal(streakDays(history, NOW), 1);
});

test("an empty history has no streak", () => {
  assert.equal(streakDays([], NOW), 0);
});

test("sessions group by day, oldest first", () => {
  const history = [h("civil", "yes", NOW), h("civil", "no", NOW - DAY)];
  const days = sessionsByDay(history);
  assert.equal(days.length, 2);
  assert.ok(days[0].day < days[1].day);
  assert.equal(days[1].count, 1);
});

test("days until the exam never goes negative", () => {
  assert.equal(daysUntil("2026-09-06", NOW), 27);
  assert.equal(daysUntil("2020-01-01", NOW), 0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test app/progress.test.js`
Expected: FAIL — cannot find module `./progress.js`

- [ ] **Step 3: Write progress**

Create `app/progress.js`:

```javascript
// Statistics derived from history. Pure functions — no storage, no DOM.

const DAY = 86400000;

// "partly" earns half credit: partial recall is real progress, and scoring it
// zero makes the number feel punitive enough to stop being useful.
const WEIGHT = { yes: 1, partly: 0.5, no: 0 };

function pct(entries) {
  if (!entries.length) return 0;
  const earned = entries.reduce((sum, e) => sum + (WEIGHT[e.grade] ?? 0), 0);
  return Math.round((earned / entries.length) * 100);
}

const dayKey = (ms) => new Date(ms).toISOString().slice(0, 10);

export function accuracy(history) {
  return pct(history);
}

export function accuracyBySubject(history) {
  const groups = {};
  for (const entry of history) {
    (groups[entry.subject] ||= []).push(entry);
  }
  return Object.fromEntries(Object.entries(groups).map(([s, e]) => [s, pct(e)]));
}

export function weakestSubject(history, minimum) {
  const groups = {};
  for (const entry of history) {
    (groups[entry.subject] ||= []).push(entry);
  }
  const eligible = Object.entries(groups).filter(([, e]) => e.length >= minimum);
  if (!eligible.length) return null;
  return eligible.sort((a, b) => pct(a[1]) - pct(b[1]))[0][0];
}

export function streakDays(history, now) {
  if (!history.length) return 0;
  const days = new Set(history.map((e) => dayKey(e.at)));

  // Start from today if studied today, otherwise yesterday — so an unfinished
  // day does not appear to break a streak that is still alive.
  let cursor = days.has(dayKey(now)) ? now : now - DAY;
  if (!days.has(dayKey(cursor))) return 0;

  let count = 0;
  while (days.has(dayKey(cursor))) {
    count++;
    cursor -= DAY;
  }
  return count;
}

export function sessionsByDay(history) {
  const groups = {};
  for (const entry of history) {
    (groups[dayKey(entry.at)] ||= []).push(entry);
  }
  return Object.entries(groups)
    .map(([day, entries]) => ({ day, count: entries.length, accuracy: pct(entries) }))
    .sort((a, b) => (a.day < b.day ? -1 : 1));
}

export function daysUntil(examDate, now) {
  return Math.max(0, Math.ceil((new Date(examDate) - now) / DAY));
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test app/progress.test.js`
Expected: PASS — 13 tests

- [ ] **Step 5: Commit**

```bash
git add app/progress.js app/progress.test.js
git commit -m "feat: add progress statistics"
```

---

### Task 4: Screens and styling

**Files:**
- Modify: `index.html`
- Modify: `app/style.css`
- Create: `app/render.js`

**Interfaces:**
- Consumes: items, cards, notes, progress functions
- Produces:
  - `renderQuestion(item, elements) -> void`
  - `renderAuthorities(authorities, container) -> void`
  - `renderProgress(history, container) -> void`
  - `escapeHtml(s) -> string`

- [ ] **Step 1: Rewrite `index.html` with five screens**

Replace the whole file:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>Bar Review</title>
<link rel="stylesheet" href="app/style.css">
</head>
<body>

<a class="skip" href="#main">Skip to main content</a>

<header>
  <button id="nav-home" class="link" type="button">Bar Review</button>
  <nav>
    <button id="nav-progress" class="link" type="button">My progress</button>
    <button id="nav-library" class="link" type="button">Search the law</button>
    <button id="nav-settings" class="link" type="button">Settings</button>
  </nav>
</header>

<main id="main">

  <section id="home" class="screen">
    <p id="status" class="status">Loading&hellip;</p>
    <button id="start" class="big" type="button">Start today's review</button>
    <p id="countdown" class="quiet"></p>
    <button id="pick" class="link" type="button">Choose a subject instead</button>
    <div id="picker" hidden></div>
  </section>

  <section id="session" class="screen" hidden>
    <p id="progress-line" class="quiet"></p>

    <article class="card">
      <p id="q-type" class="badge"></p>
      <p id="q-question" class="legal"></p>
      <p id="q-call"></p>

      <div id="answer" hidden>
        <h2 class="answer-heading">Answer key</h2>
        <p id="q-answer"></p>
        <p class="aid-note">This explanation is a study aid. The quoted law below is the authority.</p>
        <div id="authorities"></div>
        <p class="verified">Quotes verified against the corpus &middot; law as of 30 June 2025</p>
      </div>
    </article>

    <button id="reveal" class="big" type="button">Show the answer key</button>

    <div id="grading" hidden>
      <p class="grade-prompt">Did you get it right?</p>
      <div id="grades">
        <button class="grade no" type="button" data-grade="no">No</button>
        <button class="grade partly" type="button" data-grade="partly">Partly</button>
        <button class="grade yes" type="button" data-grade="yes">Yes</button>
      </div>
      <label for="note">Your notes on this question</label>
      <textarea id="note" rows="3"></textarea>
    </div>

    <button id="end" class="link" type="button">End this session</button>
  </section>

  <section id="done" class="screen" hidden>
    <h2>Session finished</h2>
    <p id="done-summary"></p>
    <button id="done-home" class="big" type="button">Back to start</button>
  </section>

  <section id="progress" class="screen" hidden>
    <h2>My progress</h2>
    <div id="progress-body"></div>
  </section>

  <section id="library" class="screen" hidden>
    <h2>Search the law</h2>
    <label for="q">Type a word or phrase</label>
    <input id="q" type="search" autocomplete="off" placeholder="rescission">
    <p id="results-count" class="quiet"></p>
    <div id="results"></div>
  </section>

  <section id="settings" class="screen" hidden>
    <h2>Settings</h2>

    <label for="exam-date">Your exam date</label>
    <input id="exam-date" type="date">

    <label for="new-limit">New questions per day</label>
    <input id="new-limit" type="number" min="0" max="200" step="5">
    <p class="quiet">Start low. Twenty a day is six hundred a month.</p>

    <fieldset>
      <legend>Subjects to study</legend>
      <div id="subjects"></div>
    </fieldset>

    <h3>Your progress file</h3>
    <p class="quiet">Everything stays on this device. Nothing is uploaded.</p>
    <button id="export" class="secondary" type="button">Save a backup file</button>
    <label for="import">Restore from a backup file</label>
    <input id="import" type="file" accept="application/json">
    <p id="settings-msg" class="quiet" role="status"></p>

    <h3>About the law in this app</h3>
    <p class="quiet" id="about-corpus"></p>
  </section>

</main>

<script type="module" src="app/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Rewrite `app/style.css`**

Replace the whole file:

```css
/* Readability first. The reader is 50, non-technical, and reading for hours. */

:root {
  --bg: #fdfcfa;
  --surface: #ffffff;
  --fg: #1b1b1a;
  --quiet: #5c5b57;
  --line: #ddd9d2;
  --accent: #17548c;
  --accent-fg: #ffffff;
  --no: #9c2f2f;
  --partly: #8a6410;
  --yes: #23603a;
  --measure: 68ch;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15161a;
    --surface: #1c1e23;
    --fg: #ecebe7;
    --quiet: #a5a39d;
    --line: #343740;
    --accent: #7db4e8;
    --accent-fg: #10141a;
    --no: #e59191;
    --partly: #dcb96a;
    --yes: #8ecda4;
  }
}

* { box-sizing: border-box; }

/* A display rule beats the hidden attribute, which would leak the answer. */
[hidden] { display: none !important; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font: 17px/1.7 system-ui, -apple-system, "Segoe UI", sans-serif;
}

.skip {
  position: absolute;
  left: -9999px;
}
.skip:focus {
  left: 1rem;
  top: 0.5rem;
  background: var(--accent);
  color: var(--accent-fg);
  padding: 0.6rem 1rem;
  border-radius: 8px;
  z-index: 10;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem 1.5rem;
  flex-wrap: wrap;
  padding: 0.9rem 1.25rem;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}
header nav { display: flex; gap: 1.5rem; flex-wrap: wrap; }

main {
  max-width: var(--measure);
  margin: 0 auto;
  padding: 2.5rem 1.25rem 6rem;
}

h2 { font-size: 1.4rem; margin: 0 0 1.25rem; line-height: 1.35; }
h3 { font-size: 1.1rem; margin: 2.5rem 0 0.5rem; }

.quiet { color: var(--quiet); font-size: 0.95rem; }
.status { font-size: 1.05rem; margin: 0 0 1.5rem; }

/* Legal prose is serif. UI chrome stays sans. */
.legal, #q-answer, .quote-text, .result-text {
  font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
  line-height: 1.7;
}

button { font: inherit; cursor: pointer; }

:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}

.big {
  display: block;
  width: 100%;
  padding: 1.15rem 1.25rem;
  margin: 0 0 1.25rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--accent-fg);
  background: var(--accent);
  border: none;
  border-radius: 10px;
}
.big:hover { filter: brightness(1.1); }

.secondary {
  padding: 0.75rem 1.25rem;
  background: var(--surface);
  color: var(--fg);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.link {
  background: none;
  border: none;
  padding: 0.25rem 0;
  color: var(--accent);
  font-size: 1rem;
  text-decoration: underline;
}

#picker { display: grid; gap: 0.6rem; margin-top: 1rem; }
.mode {
  padding: 1rem 1.15rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  color: var(--fg);
  text-align: left;
  font-size: 1.05rem;
}
.mode:hover { border-color: var(--accent); }

.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1.75rem;
  margin-bottom: 1.5rem;
}

.badge {
  display: inline-block;
  margin: 0 0 1rem;
  padding: 0.3rem 0.8rem;
  border-radius: 999px;
  background: var(--bg);
  border: 1px solid var(--line);
  font-size: 0.85rem;
  color: var(--quiet);
}

#q-question { margin: 0 0 1.25rem; }
#q-call { font-weight: 600; margin: 0 0 0.5rem; }

.answer-heading {
  font-size: 1.1rem;
  margin: 1.75rem 0 0.75rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--line);
  color: var(--yes);
}

.aid-note, .verified {
  font-size: 0.9rem;
  color: var(--quiet);
  margin: 1rem 0;
}

.quote {
  background: var(--bg);
  border-left: 4px solid var(--accent);
  border-radius: 0;
  padding: 1rem 1.25rem;
  margin: 1rem 0;
}
.quote-cite { font-weight: 600; margin: 0 0 0.5rem; color: var(--accent); }
.quote-text { margin: 0 0 0.75rem; font-size: 1rem; }

.grade-prompt { margin: 0 0 0.75rem; font-weight: 600; }
#grades { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
.grade {
  padding: 1.1rem 0.5rem;
  border: 2px solid;
  border-radius: 10px;
  background: var(--surface);
  font-size: 1.05rem;
  font-weight: 600;
}
.no { color: var(--no); border-color: var(--no); }
.partly { color: var(--partly); border-color: var(--partly); }
.yes { color: var(--yes); border-color: var(--yes); }
.grade:hover { filter: brightness(1.12); }

label { display: block; margin: 1.5rem 0 0.4rem; font-weight: 600; font-size: 1rem; }

input[type="search"], input[type="date"], input[type="number"], textarea {
  width: 100%;
  padding: 0.8rem;
  font: inherit;
  color: var(--fg);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
}
textarea { resize: vertical; }

fieldset { border: 1px solid var(--line); border-radius: 10px; margin: 1.5rem 0; padding: 1rem 1.25rem; }
legend { padding: 0 0.4rem; font-weight: 600; }
#subjects label { display: flex; align-items: center; gap: 0.6rem; margin: 0.6rem 0; font-weight: 400; }
#subjects input { width: 1.15rem; height: 1.15rem; }

.result { border-top: 1px solid var(--line); padding: 1.25rem 0; }
.result-cite { font-weight: 600; margin: 0 0 0.4rem; }
.result-text { margin: 0; }
mark { background: #ffe98a; color: #1b1b1a; padding: 0 0.15em; }

.stat { display: flex; justify-content: space-between; gap: 1rem; padding: 0.85rem 0; border-bottom: 1px solid var(--line); }
.stat-label { color: var(--quiet); }
.stat-value { font-weight: 600; }

.bar { height: 0.6rem; background: var(--line); border-radius: 999px; overflow: hidden; margin-top: 0.35rem; }
.bar span { display: block; height: 100%; background: var(--accent); }
```

- [ ] **Step 3: Write `app/render.js`**

```javascript
// DOM rendering only. No business logic, no storage.

const TYPE_LABELS = {
  hypothetical: "Hypothetical",
  issue_spotting: "Issue spotting",
  essay: "Essay",
  doctrine: "Doctrine",
};

export function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

/** Split "facts ... question?" into a fact pattern and the call of the question. */
export function splitCall(question) {
  const trimmed = question.trim();
  const lastQuestionMark = trimmed.lastIndexOf("?");
  if (lastQuestionMark === -1) return { facts: trimmed, call: "" };

  const before = trimmed.slice(0, lastQuestionMark + 1);
  const boundary = Math.max(before.lastIndexOf(". "), before.lastIndexOf("\n"));
  if (boundary === -1) return { facts: "", call: before };
  return { facts: before.slice(0, boundary + 1).trim(), call: before.slice(boundary + 1).trim() };
}

export function renderQuestion(item, el) {
  const { facts, call } = splitCall(item.question);
  el.type.textContent = TYPE_LABELS[item.type] || item.type;
  el.question.textContent = facts;
  el.question.hidden = !facts;
  el.call.textContent = call || item.question;
  el.answer.textContent = item.answer_key;
}

export function renderAuthorities(authorities, container) {
  container.textContent = "";
  for (const a of authorities) {
    const box = document.createElement("div");
    box.className = "quote";

    const cite = document.createElement("p");
    cite.className = "quote-cite";
    cite.textContent = a.citation;

    const text = document.createElement("p");
    text.className = "quote-text";
    text.textContent = `"${a.quote}"`;

    const link = document.createElement("a");
    link.href = a.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Read the full text on the official source";

    box.append(cite, text, link);
    container.appendChild(box);
  }
}

function stat(label, value) {
  const row = document.createElement("div");
  row.className = "stat";
  const l = document.createElement("span");
  l.className = "stat-label";
  l.textContent = label;
  const v = document.createElement("span");
  v.className = "stat-value";
  v.textContent = value;
  row.append(l, v);
  return row;
}

export function renderProgress(stats, container) {
  container.textContent = "";

  container.appendChild(stat("Questions answered", String(stats.total)));
  container.appendChild(stat("Accuracy overall", `${stats.accuracy}%`));
  container.appendChild(stat("Current streak", `${stats.streak} day${stats.streak === 1 ? "" : "s"}`));
  container.appendChild(stat("Days until the Bar", String(stats.daysLeft)));

  const heading = document.createElement("h3");
  heading.textContent = "Accuracy by subject";
  container.appendChild(heading);

  const entries = Object.entries(stats.bySubject);
  if (!entries.length) {
    const p = document.createElement("p");
    p.className = "quiet";
    p.textContent = "Answer some questions and your scores will appear here.";
    container.appendChild(p);
    return;
  }

  for (const [subject, pct] of entries.sort((a, b) => a[1] - b[1])) {
    const row = stat(stats.subjectNames[subject] || subject, `${pct}%`);
    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("span");
    fill.style.width = `${pct}%`;
    bar.appendChild(fill);
    const wrap = document.createElement("div");
    wrap.append(row, bar);
    container.appendChild(wrap);
  }
}
```

- [ ] **Step 4: Write a render test**

Create `app/render.test.js`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { escapeHtml, splitCall } from "./render.js";

test("html is escaped", () => {
  assert.equal(escapeHtml("<script>x</script>"), "&lt;script&gt;x&lt;/script&gt;");
});

test("the call of the question is split from the facts", () => {
  const { facts, call } = splitCall(
    "Ana sold a lot to Ben. Ben stopped paying. May Ana rescind?"
  );
  assert.equal(facts, "Ana sold a lot to Ben. Ben stopped paying.");
  assert.equal(call, "May Ana rescind?");
});

test("a question with no facts still yields a call", () => {
  const { facts, call } = splitCall("What are the elements of estafa?");
  assert.equal(facts, "");
  assert.equal(call, "What are the elements of estafa?");
});

test("a statement with no question mark is all facts", () => {
  const { facts, call } = splitCall("List the elements of estafa.");
  assert.equal(call, "");
  assert.ok(facts.length > 0);
});
```

- [ ] **Step 5: Run the tests**

Run: `node --test app/`
Expected: PASS — all test files, including the existing `sm2.test.js`

- [ ] **Step 6: Commit**

```bash
git add index.html app/style.css app/render.js app/render.test.js
git commit -m "feat: rebuild screens with readable legal typography"
```

---

### Task 5: Wire it together

**Files:**
- Modify: `app/app.js`
- Modify: `sw.js`

**Interfaces:**
- Consumes: everything from Tasks 1-4, plus `bank/questions.json` and `corpus/provisions.json`

- [ ] **Step 1: Rewrite `app/app.js`**

```javascript
// Wiring only. Logic lives in store.js, session.js, progress.js, render.js.

import {
  accuracy,
  accuracyBySubject,
  daysUntil,
  streakDays,
  weakestSubject,
} from "./progress.js";
import { renderAuthorities, renderProgress, renderQuestion } from "./render.js";
import { gradeItem, startSession } from "./session.js";
import { createStore } from "./store.js";

const SUBJECT_NAMES = {
  remedial: "Remedial Law",
  civil: "Civil Law",
  commercial_tax: "Commercial and Tax",
  political: "Political Law",
  labor: "Labor Law",
  criminal: "Criminal Law",
};

const $ = (id) => document.getElementById(id);
const store = createStore(localStorage);

let items = [];
let provisions = [];
let queue = [];
let current = null;
let answered = 0;

function show(name) {
  for (const el of document.querySelectorAll(".screen")) el.hidden = el.id !== name;
  window.scrollTo(0, 0);
}

function refreshHome() {
  const settings = store.getSettings();
  const history = store.getHistory();
  const cards = store.getCards();
  const { queue: preview } = startSession({
    items,
    cards,
    settings,
    subject: null,
    now: Date.now(),
  });

  const weakest = weakestSubject(history, 5);
  const parts = [`${preview.length} question${preview.length === 1 ? "" : "s"} ready`];
  if (history.length) parts.push(`${accuracy(history)}% right so far`);
  if (weakest) parts.push(`weakest: ${SUBJECT_NAMES[weakest] || weakest}`);
  $("status").textContent = parts.join(" · ");

  $("countdown").textContent =
    `${daysUntil(settings.examDate, Date.now())} days until the Bar · law as of 30 June 2025`;
}

function renderPicker() {
  const box = $("picker");
  box.textContent = "";
  const subjects = [...new Set(items.map((i) => i.subject))].sort();

  const all = document.createElement("button");
  all.type = "button";
  all.className = "mode";
  all.textContent = "Everything";
  all.addEventListener("click", () => begin(null));
  box.appendChild(all);

  for (const s of subjects) {
    const count = items.filter((i) => i.subject === s).length;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "mode";
    b.textContent = `${SUBJECT_NAMES[s] || s} (${count} questions)`;
    b.addEventListener("click", () => begin(s));
    box.appendChild(b);
  }
}

function begin(subject) {
  const result = startSession({
    items,
    cards: store.getCards(),
    settings: store.getSettings(),
    subject,
    now: Date.now(),
  });
  queue = result.queue;
  answered = 0;

  if (!queue.length) {
    $("status").textContent = "No questions available for that choice yet.";
    show("home");
    return;
  }
  nextItem();
}

function nextItem() {
  if (!queue.length) return finish();

  current = queue.shift();
  renderQuestion(current, {
    type: $("q-type"),
    question: $("q-question"),
    call: $("q-call"),
    answer: $("q-answer"),
  });
  renderAuthorities(current.authorities, $("authorities"));

  $("note").value = store.getNote(current.id);
  $("answer").hidden = true;
  $("grading").hidden = true;
  $("reveal").hidden = false;
  $("progress-line").textContent = `${queue.length + 1} left in this session`;

  show("session");
}

function reveal() {
  $("answer").hidden = false;
  $("reveal").hidden = true;
  $("grading").hidden = false;
}

function grade(name) {
  if ($("grading").hidden) return;

  const cards = store.getCards();
  const card = cards[current.id] || { id: current.id, ease: 2.5, interval: 0, reps: 0, due: 0, lapses: 0 };
  const { card: updated, historyEntry } = gradeItem({
    item: current,
    card,
    grade: name,
    now: Date.now(),
  });

  store.setNote(current.id, $("note").value);
  store.setCard(updated);
  store.appendHistory(historyEntry);
  answered++;

  if (name === "no") queue.push(current);
  nextItem();
}

function finish() {
  $("done-summary").textContent =
    `You answered ${answered} question${answered === 1 ? "" : "s"}.`;
  show("done");
  refreshHome();
}

function showProgress() {
  const history = store.getHistory();
  renderProgress(
    {
      total: history.length,
      accuracy: accuracy(history),
      streak: streakDays(history, Date.now()),
      daysLeft: daysUntil(store.getSettings().examDate, Date.now()),
      bySubject: accuracyBySubject(history),
      subjectNames: SUBJECT_NAMES,
    },
    $("progress-body")
  );
  show("progress");
}

function search(term) {
  const results = $("results");
  results.textContent = "";
  const q = term.trim().toLowerCase();

  if (q.length < 3) {
    $("results-count").textContent = "Type at least three letters.";
    return;
  }

  // ponytail: linear scan over a few thousand provisions is instant. Build an
  // index only if the corpus grows past that.
  const hits = provisions.filter((p) => p.text.toLowerCase().includes(q)).slice(0, 50);
  $("results-count").textContent = hits.length
    ? `${hits.length} result${hits.length === 1 ? "" : "s"}`
    : "Nothing found.";

  for (const p of hits) {
    const i = p.text.toLowerCase().indexOf(q);
    const start = Math.max(0, i - 90);

    const div = document.createElement("div");
    div.className = "result";

    const cite = document.createElement("p");
    cite.className = "result-cite";
    cite.textContent = p.citation;

    const text = document.createElement("p");
    text.className = "result-text";
    text.append(
      document.createTextNode((start > 0 ? "…" : "") + p.text.slice(start, i))
    );
    const hit = document.createElement("mark");
    hit.textContent = p.text.slice(i, i + q.length);
    text.append(hit, document.createTextNode(p.text.slice(i + q.length, i + 220) + "…"));

    div.append(cite, text);
    results.appendChild(div);
  }
}

function renderSettings() {
  const settings = store.getSettings();
  $("exam-date").value = settings.examDate;
  $("new-limit").value = settings.newLimit;

  const box = $("subjects");
  box.textContent = "";
  for (const s of [...new Set(items.map((i) => i.subject))].sort()) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = settings.subjects.includes(s);
    input.addEventListener("change", () => {
      const currentSubjects = store.getSettings().subjects;
      store.setSettings({
        subjects: input.checked
          ? [...new Set([...currentSubjects, s])]
          : currentSubjects.filter((x) => x !== s),
      });
      refreshHome();
    });
    label.append(input, ` ${SUBJECT_NAMES[s] || s}`);
    box.appendChild(label);
  }
}

async function main() {
  try {
    const [bank, provs] = await Promise.all([
      fetch("bank/questions.json").then((r) => (r.ok ? r.json() : [])),
      fetch("corpus/provisions.json").then((r) => (r.ok ? r.json() : [])),
    ]);
    items = bank;
    provisions = provs;
  } catch (err) {
    $("status").textContent =
      `Could not load the questions (${err.message}). If this is your first visit, connect once and reload.`;
    $("start").hidden = true;
    return;
  }

  if (!items.length) {
    $("status").textContent = "No questions are loaded yet.";
    $("start").hidden = true;
  }

  const manifest = await fetch("corpus/manifest.json")
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  $("about-corpus").textContent = manifest
    ? `${items.length} questions drawn from ${manifest.total} official documents. Coverage cut-off ${manifest.coverage_date}. Every quotation is checked against the source text before it ships.`
    : `${items.length} questions loaded.`;

  renderPicker();
  renderSettings();
  refreshHome();

  $("start").addEventListener("click", () => begin(null));
  $("pick").addEventListener("click", () => {
    $("picker").hidden = !$("picker").hidden;
  });
  $("reveal").addEventListener("click", reveal);
  for (const b of document.querySelectorAll(".grade")) {
    b.addEventListener("click", () => grade(b.dataset.grade));
  }
  $("end").addEventListener("click", finish);
  $("done-home").addEventListener("click", () => show("home"));

  $("nav-home").addEventListener("click", () => {
    refreshHome();
    show("home");
  });
  $("nav-progress").addEventListener("click", showProgress);
  $("nav-library").addEventListener("click", () => show("library"));
  $("nav-settings").addEventListener("click", () => {
    renderSettings();
    show("settings");
  });

  $("q").addEventListener("input", (e) => search(e.target.value));
  $("exam-date").addEventListener("change", (e) => {
    store.setSettings({ examDate: e.target.value });
    refreshHome();
  });
  $("new-limit").addEventListener("change", (e) => {
    store.setSettings({ newLimit: Math.max(0, Number(e.target.value) || 0) });
    refreshHome();
  });

  $("export").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(store.exportAll(), null, 1)], {
      type: "application/json",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bar-review-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    $("settings-msg").textContent = "Backup saved to your downloads.";
  });

  $("import").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      store.importAll(JSON.parse(await file.text()));
      renderSettings();
      refreshHome();
      $("settings-msg").textContent = "Your progress was restored.";
    } catch (err) {
      $("settings-msg").textContent = err.message;
    }
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

main();
```

- [ ] **Step 2: Update the service worker cache list**

In `sw.js`, change `CACHE` to `"barrev-v2"` and replace `SHELL` with:

```javascript
const SHELL = [
  "./",
  "./index.html",
  "./app/app.js",
  "./app/sm2.js",
  "./app/store.js",
  "./app/session.js",
  "./app/progress.js",
  "./app/render.js",
  "./app/style.css",
  "./bank/questions.json",
  "./corpus/provisions.json",
  "./corpus/manifest.json",
];
```

- [ ] **Step 3: Run all tests**

```bash
node --test app/ && .venv/bin/pytest -q
```

Expected: all JS tests pass, all Python tests pass.

- [ ] **Step 4: Verify in a browser**

```bash
python3 -m http.server 8127
```

Open `http://localhost:8127`. Confirm, by clicking:

1. Home shows a question count and one primary button.
2. `Start today's review` shows a question with the answer hidden.
3. `Show the answer key` reveals the key, the quoted authority, the study-aid
   note, and the three grade buttons.
4. Grading advances to the next question.
5. A note typed on a question is still there when that question returns.
6. `My progress` shows totals and per-subject accuracy.
7. `Search the law` returns highlighted results.
8. Settings export downloads a file; re-importing it restores progress.
9. Tab through every screen — focus is always visible.

- [ ] **Step 5: Commit**

```bash
git add app/app.js sw.js
git commit -m "feat: wire the scenario-question study session"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| §7 self-grading No/Partly/Yes | Task 2, Task 4 |
| §7 progress, accuracy, streak, weakest subject | Task 3 |
| §8 five screens | Task 4 |
| §8 notes on questions | Tasks 1, 5 |
| §8 readability rules | Task 4 (`style.css`) |
| §3 no runtime AI, local only | Task 5 (fetches static files only) |
| §4 reasoning labelled a study aid | Task 4 (`.aid-note` in `index.html`) |

**Deliberate limitations:**

- Notes attach to questions in this plan. Notes on arbitrary provisions from
  the Library screen are supported by the store but not yet surfaced in the UI.
  *ponytail: question notes only; add library notes when the reading view lands.*
- Search is a linear scan. Fine to a few thousand provisions.
