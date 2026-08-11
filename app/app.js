// Wiring only. Logic lives in store.js, session.js, progress.js, render.js.

import { accuracy, daysUntil, streakDays, weakestSubject } from "./progress.js";
import { renderQuestion } from "./render.js";
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
  const { queue: preview } = startSession({
    items,
    cards: store.getCards(),
    settings,
    subject: null,
    now: Date.now(),
  });

  $("status").textContent = preview.length
    ? `${preview.length} question${preview.length === 1 ? "" : "s"} ready for you.`
    : "Nothing due right now. Start anyway to study ahead.";

  // One quiet line carries everything the old progress screen showed.
  const weakest = weakestSubject(history, 5);
  const bits = [`${daysUntil(settings.examDate, Date.now())} days until the Bar`];
  if (history.length) {
    bits.push(`${history.length} answered`, `${accuracy(history)}% right`);
    const streak = streakDays(history, Date.now());
    if (streak > 1) bits.push(`${streak}-day streak`);
    if (weakest) bits.push(`weakest: ${SUBJECT_NAMES[weakest] || weakest}`);
  }
  $("scoreline").textContent = bits.join(" · ");
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
    b.textContent = `${SUBJECT_NAMES[s] || s} (${count} question${count === 1 ? "" : "s"})`;
    b.addEventListener("click", () => begin(s));
    box.appendChild(b);
  }
}

function begin(subject) {
  const { queue: built } = startSession({
    items,
    cards: store.getCards(),
    settings: store.getSettings(),
    subject,
    now: Date.now(),
  });
  queue = built;
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
    exceptions: $("q-exceptions"),
    exceptionsBlock: $("exceptions-block"),
    controlling: $("controlling"),
    controllingBlock: $("controlling-block"),
    related: $("related"),
    relatedBlock: $("related-block"),
  });

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
  const card = cards[current.id] || {
    id: current.id,
    ease: 2.5,
    interval: 0,
    reps: 0,
    due: 0,
    lapses: 0,
  };
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
  refreshHome();
  $("status").textContent = answered
    ? `You answered ${answered} question${answered === 1 ? "" : "s"}. ${$("status").textContent}`
    : $("status").textContent;
  show("home");
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
    text.append(document.createTextNode((start > 0 ? "…" : "") + p.text.slice(start, i)));
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

// Provisions are several megabytes and only the Search screen needs them.
// Loading them lazily keeps first paint instant no matter how large the
// corpus grows — questions carry their own quotes, so drilling needs nothing else.
let provisionsPromise = null;

function loadProvisions() {
  if (!provisionsPromise) {
    provisionsPromise = fetch("corpus/provisions.json")
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        provisions = data;
        return data;
      })
      .catch(() => {
        provisionsPromise = null;
        return [];
      });
  }
  return provisionsPromise;
}

async function main() {
  try {
    items = await fetch("bank/questions.json").then((r) => (r.ok ? r.json() : []));
  } catch (err) {
    $("status").textContent =
      `Could not load the questions (${err.message}). If this is your first visit, connect once and reload.`;
    $("start").hidden = true;
    return;
  }

  if (!items.length) {
    $("status").textContent =
      "No practice questions are loaded yet. You can still search the law.";
    $("start").hidden = true;
    $("pick").hidden = true;
  }

  // Manifest is tiny and non-blocking; the app is already usable without it.
  fetch("corpus/manifest.json")
    .then((r) => (r.ok ? r.json() : null))
    .then((manifest) => {
      $("about-corpus").textContent = manifest
        ? `${items.length} questions drawn from ${manifest.total} official documents. Coverage cut-off ${manifest.coverage_date}. Every quotation is checked word-for-word against the source before it ships.`
        : `${items.length} questions loaded.`;
    })
    .catch(() => {});

  renderPicker();
  renderSettings();
  refreshHome();

  $("start").addEventListener("click", () => begin(null));
  $("reveal").addEventListener("click", reveal);
  for (const b of document.querySelectorAll(".grade")) {
    b.addEventListener("click", () => grade(b.dataset.grade));
  }
  $("end").addEventListener("click", finish);

  $("nav-home").addEventListener("click", () => {
    refreshHome();
    show("home");
  });
  $("nav-library").addEventListener("click", async () => {
    show("library");
    if (!provisions.length) {
      $("results-count").textContent = "Loading the law\u2026";
      await loadProvisions();
      $("results-count").textContent = provisions.length
        ? "Type at least three letters."
        : "Could not load the law. Check your connection and try again.";
    }
  });
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
