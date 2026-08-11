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
