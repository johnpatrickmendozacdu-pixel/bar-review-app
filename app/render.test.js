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
