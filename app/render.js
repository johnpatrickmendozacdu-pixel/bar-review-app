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
