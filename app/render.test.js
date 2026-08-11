import assert from "node:assert/strict";
import test from "node:test";

import { escapeHtml, isCase, renderQuestion, splitCall } from "./render.js";

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

test("type labels cover every item type", () => {
  const stub = () => ({ textContent: "", hidden: false });
  const el = {
    type: stub(), question: stub(), call: stub(), answer: stub(),
    exceptions: stub(), exceptionsBlock: stub(),
    controlling: { textContent: "", appendChild() {} },
    controllingBlock: stub(),
    relatedProvisions: { textContent: "", appendChild() {} },
    relatedProvisionsBlock: stub(),
    related: { textContent: "", appendChild() {} },
    relatedBlock: stub(),
  };
  renderQuestion(
    { type: "issue_spotting", question: "Facts. What now?", answer_key: "A", exceptions: "", authorities: [] },
    el
  );
  assert.equal(el.type.textContent, "Issue spotting");
});

test("an empty exceptions field hides its whole block", () => {
  const stub = () => ({ textContent: "", hidden: false });
  const el = {
    type: stub(), question: stub(), call: stub(), answer: stub(),
    exceptions: stub(), exceptionsBlock: stub(),
    controlling: { textContent: "", appendChild() {} },
    controllingBlock: stub(),
    relatedProvisions: { textContent: "", appendChild() {} },
    relatedProvisionsBlock: stub(),
    related: { textContent: "", appendChild() {} },
    relatedBlock: stub(),
  };
  renderQuestion({ type: "doctrine", question: "Q?", answer_key: "A", exceptions: "   ", authorities: [] }, el);
  assert.equal(el.exceptionsBlock.hidden, true);
});

test("cases and provisions are told apart by document id", () => {
  assert.equal(isCase("gr-102858"), true);
  assert.equal(isCase("am-93-2-1011-rtc"), true);
  assert.equal(isCase("ra-386-art-19"), false);
  assert.equal(isCase("pd-442-art-282"), false);
});
