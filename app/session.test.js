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
