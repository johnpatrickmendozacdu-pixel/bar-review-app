// Run: node app/sm2.test.js
import assert from "node:assert/strict";
import test from "node:test";
import {
  AGAIN,
  GOOD,
  HARD,
  MIN_EASE,
  buildQueue,
  dueCards,
  newCard,
  review,
} from "./sm2.js";

const DAY = 86400000;
const T0 = 1000000000000;

test("a new card is due immediately and unstudied", () => {
  const c = newCard("ra-386-art-1191");
  assert.equal(c.reps, 0);
  assert.equal(c.interval, 0);
  assert.equal(c.ease, 2.5);
});

test("first correct answer schedules one day out", () => {
  const c = review(newCard("x"), GOOD, T0);
  assert.equal(c.reps, 1);
  assert.equal(c.interval, 1);
  assert.equal(c.due, T0 + DAY);
});

test("second correct answer schedules six days out", () => {
  const c = review(review(newCard("x"), GOOD, T0), GOOD, T0);
  assert.equal(c.interval, 6);
});

test("intervals grow by the ease factor after the second review", () => {
  let c = review(review(newCard("x"), GOOD, T0), GOOD, T0);
  const before = c.interval;
  c = review(c, GOOD, T0);
  assert.ok(c.interval > before, `expected growth, got ${c.interval}`);
  assert.equal(c.interval, Math.round(before * c.ease));
});

test("forgetting resets the ladder and counts a lapse", () => {
  let c = review(review(newCard("x"), GOOD, T0), GOOD, T0);
  c = review(c, AGAIN, T0);
  assert.equal(c.reps, 0);
  assert.equal(c.interval, 0);
  assert.equal(c.lapses, 1);
  assert.equal(c.due, T0, "a forgotten card must come back in this session");
});

test("ease drops when a card is hard and rises when it is easy", () => {
  const hard = review(newCard("x"), HARD, T0);
  const good = review(newCard("x"), GOOD, T0);
  assert.ok(hard.ease < 2.5, `hard ease ${hard.ease}`);
  assert.ok(good.ease > 2.5, `good ease ${good.ease}`);
});

test("ease never falls below the floor", () => {
  let c = newCard("x");
  for (let i = 0; i < 40; i++) c = review(c, AGAIN, T0);
  assert.ok(c.ease >= MIN_EASE, `ease fell to ${c.ease}`);
});

test("review does not mutate its input", () => {
  const c = newCard("x");
  const snapshot = JSON.stringify(c);
  review(c, GOOD, T0);
  assert.equal(JSON.stringify(c), snapshot);
});

test("cards not yet due are excluded", () => {
  const c = review(newCard("x"), GOOD, T0);
  assert.equal(dueCards([c], T0).length, 0);
  assert.equal(dueCards([c], T0 + DAY).length, 1);
});

test("due cards come before new cards in the queue", () => {
  const dueCard = { ...review(newCard("due"), GOOD, T0), due: T0 };
  const freshCard = newCard("fresh");
  const q = buildQueue([freshCard, dueCard], T0, 10);
  assert.equal(q[0].id, "due");
});

test("new cards are capped by the daily limit", () => {
  const cards = Array.from({ length: 50 }, (_, i) => newCard(`c${i}`));
  assert.equal(buildQueue(cards, T0, 20).length, 20);
});

test("a full study lifecycle reaches month-long intervals", () => {
  let c = newCard("x");
  let now = T0;
  for (let i = 0; i < 5; i++) {
    c = review(c, GOOD, now);
    now = c.due;
  }
  assert.ok(c.interval > 30, `expected >30 days after 5 clean reviews, got ${c.interval}`);
});
