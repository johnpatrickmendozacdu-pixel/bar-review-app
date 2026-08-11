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
