// DOM rendering only. No business logic, no storage.

const TYPE_LABELS = {
  hypothetical: "Hypothetical",
  issue_spotting: "Issue spotting",
  essay: "Essay",
  doctrine: "Doctrine",
};

// Decisions, as opposed to statutory provisions. Grouping by this rather than
// by role is what stops a Civil Code article appearing under "Related cases".
const CASE_PREFIXES = ["gr-", "am-", "ac-", "bm-"];

export function isCase(docId) {
  return CASE_PREFIXES.some((p) => String(docId).startsWith(p));
}

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
  return {
    facts: before.slice(0, boundary + 1).trim(),
    call: before.slice(boundary + 1).trim(),
  };
}

export function renderQuestion(item, el) {
  const { facts, call } = splitCall(item.question);
  el.type.textContent = TYPE_LABELS[item.type] || item.type;
  el.question.textContent = facts;
  el.question.hidden = !facts;
  el.call.textContent = call || item.question;
  el.answer.textContent = item.answer_key;

  const exceptions = (item.exceptions || "").trim();
  el.exceptions.textContent = exceptions;
  el.exceptionsBlock.hidden = !exceptions;

  // A related case is an authority with a different role, so both groups
  // render through the same code and carry the same guarantee.
  // Split by what the authority IS, not by its role. A related Civil Code
  // article is a provision, not a case, and must not sit under "Related cases".
  const all = item.authorities || [];
  const provisions = all.filter((a) => !isCase(a.doc_id));
  const cases = all.filter((a) => isCase(a.doc_id));
  const governing = provisions.filter((a) => (a.role || "controlling") === "controlling");
  const alsoRelevant = provisions.filter((a) => a.role === "related");

  renderAuthorities(governing, el.controlling);
  el.controllingBlock.hidden = !governing.length;

  renderAuthorities(alsoRelevant, el.relatedProvisions);
  el.relatedProvisionsBlock.hidden = !alsoRelevant.length;

  renderAuthorities(cases, el.related);
  el.relatedBlock.hidden = !cases.length;
}

export function renderAuthorities(authorities, container) {
  container.textContent = "";
  for (const a of authorities) {
    const box = document.createElement("div");
    box.className = "quote";

    const cite = document.createElement("p");
    cite.className = "quote-cite";
    cite.textContent = a.citation;

    // For a decision, the story matters as much as the quote: who sued whom,
    // what was decided, and why.
    let story = null;
    if (a.context) {
      story = document.createElement("p");
      story.className = "case-context";
      story.textContent = a.context;
    }

    const text = document.createElement("p");
    text.className = "quote-text";
    text.textContent = `"${a.quote}"`;

    const link = document.createElement("a");
    link.href = a.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Read the full text on the official source";

    if (story) box.append(cite, story, text, link);
    else box.append(cite, text, link);
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
  container.appendChild(
    stat("Current streak", `${stats.streak} day${stats.streak === 1 ? "" : "s"}`)
  );
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
    const wrap = document.createElement("div");
    wrap.append(stat(stats.subjectNames[subject] || subject, `${pct}%`));
    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("span");
    fill.style.width = `${pct}%`;
    bar.appendChild(fill);
    wrap.append(bar);
    container.appendChild(wrap);
  }
}
