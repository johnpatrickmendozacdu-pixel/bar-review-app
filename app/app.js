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
  const { queue: preview } = startSession({
    items,
    cards: store.getCards(),
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
    $("status").textContent =
      "No practice questions are loaded yet. You can still search the law.";
    $("start").hidden = true;
    $("pick").hidden = true;
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
