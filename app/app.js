// Bar Review — drills over verbatim statutory provisions.
// No framework, no build step. Everything you do stays in this browser.

import { buildQueue, newCard, review } from "./sm2.js";

const CARDS_KEY = "barrev.cards";
const SETTINGS_KEY = "barrev.settings";

const DEFAULTS = {
  examDate: "2026-09-06", // Day 1 of the 2026 Bar
  newLimit: 20,
  subjects: ["civil", "criminal", "political", "commercial_tax"],
};

const SUBJECT_NAMES = {
  civil: "Civil Law",
  criminal: "Criminal Law",
  political: "Political Law",
  commercial_tax: "Commercial & Tax",
  labor: "Labor Law",
  remedial: "Remedial Law",
};

const $ = (id) => document.getElementById(id);

let provisions = [];
let cards = {};
let settings = { ...DEFAULTS };
let queue = [];
let current = null;
let reviewed = 0;

// ---------- storage ----------
// ponytail: localStorage. Progress is a few hundred KB even after a year of
// study; move to IndexedDB only if it approaches the ~5MB cap.

function load() {
  try {
    cards = JSON.parse(localStorage.getItem(CARDS_KEY)) || {};
  } catch {
    cards = {};
  }
  try {
    settings = { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(SETTINGS_KEY)) || {}) };
  } catch {
    settings = { ...DEFAULTS };
  }
}

function saveCards() {
  localStorage.setItem(CARDS_KEY, JSON.stringify(cards));
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

// ---------- screens ----------

function show(name) {
  for (const el of document.querySelectorAll(".screen")) el.hidden = el.id !== name;
  window.scrollTo(0, 0);
}

// ---------- home ----------

function activeProvisions() {
  return provisions.filter((p) => settings.subjects.includes(p.subject));
}

function cardStates() {
  return activeProvisions().map((p) => cards[p.id] || newCard(p.id));
}

function daysToExam() {
  const diff = new Date(settings.examDate) - Date.now();
  return Math.max(0, Math.ceil(diff / 86400000));
}

function refreshHome() {
  const now = Date.now();
  const all = cardStates();
  const due = buildQueue(all, now, settings.newLimit);
  const seen = all.filter((c) => c.reps > 0).length;

  $("status").textContent = due.length
    ? `${due.length} card${due.length === 1 ? "" : "s"} ready · ${seen} of ${all.length} started`
    : `Nothing due right now. ${seen} of ${all.length} started.`;

  $("start").textContent = due.length ? "Start today's review" : "Study ahead anyway";
  $("countdown").textContent = `${daysToExam()} days until the Bar · law as of 30 June 2025`;
}

// ---------- session ----------

function startSession(subject) {
  const now = Date.now();
  const pool = subject
    ? provisions.filter((p) => p.subject === subject)
    : activeProvisions();

  const states = pool.map((p) => cards[p.id] || newCard(p.id));
  queue = buildQueue(states, now, settings.newLimit);

  if (!queue.length) {
    // Nothing due: study the least-recently-seen material instead of nothing.
    queue = states.sort((a, b) => a.due - b.due).slice(0, settings.newLimit);
  }

  reviewed = 0;
  nextCard();
}

function nextCard() {
  if (!queue.length) return finishSession();

  current = queue.shift();
  const prov = provisions.find((p) => p.id === current.id);
  if (!prov) return nextCard();

  $("card-citation").textContent = prov.citation;
  $("card-text").textContent = prov.text;
  $("card-source").href = prov.source_url;
  $("card-answer").hidden = true;
  $("reveal").hidden = false;
  $("grades").hidden = true;
  $("progress").textContent = `${queue.length + 1} left in this session`;

  show("session");
}

function revealAnswer() {
  $("card-answer").hidden = false;
  $("reveal").hidden = true;
  $("grades").hidden = false;
}

function gradeCard(grade) {
  if ($("grades").hidden) return;
  const updated = review(current, grade, Date.now());
  cards[updated.id] = updated;
  saveCards();
  reviewed++;

  // A forgotten card comes back at the end of this same session.
  if (grade < 3) queue.push(updated);

  nextCard();
}

function finishSession() {
  $("done-summary").textContent = `You reviewed ${reviewed} card${reviewed === 1 ? "" : "s"}.`;
  show("done");
  refreshHome();
}

// ---------- library ----------

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function search(term) {
  const results = $("results");
  results.textContent = "";
  const q = term.trim().toLowerCase();

  if (q.length < 3) {
    $("results-count").textContent = "Type at least three letters.";
    return;
  }

  // ponytail: linear scan over ~2,900 provisions is instant. Build an index
  // only if the corpus passes a few thousand documents.
  const hits = provisions.filter((p) => p.text.toLowerCase().includes(q)).slice(0, 50);
  $("results-count").textContent = hits.length
    ? `${hits.length} result${hits.length === 1 ? "" : "s"}`
    : "Nothing found.";

  for (const p of hits) {
    const div = document.createElement("div");
    div.className = "result";
    const i = p.text.toLowerCase().indexOf(q);
    const start = Math.max(0, i - 90);
    const snippet = p.text.slice(start, i + 220);
    div.innerHTML =
      `<h3></h3><p>${start > 0 ? "…" : ""}${escapeHtml(snippet.slice(0, i - start))}` +
      `<mark>${escapeHtml(snippet.slice(i - start, i - start + q.length))}</mark>` +
      `${escapeHtml(snippet.slice(i - start + q.length))}…</p>`;
    div.querySelector("h3").textContent = p.citation;
    results.appendChild(div);
  }
}

// ---------- settings ----------

function renderSettings() {
  $("exam-date").value = settings.examDate;
  $("new-limit").value = settings.newLimit;

  const box = $("subjects");
  box.textContent = "";
  const present = [...new Set(provisions.map((p) => p.subject))].filter(Boolean);

  for (const s of present) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = settings.subjects.includes(s);
    input.addEventListener("change", () => {
      settings.subjects = input.checked
        ? [...new Set([...settings.subjects, s])]
        : settings.subjects.filter((x) => x !== s);
      saveSettings();
      refreshHome();
    });
    const count = provisions.filter((p) => p.subject === s).length;
    label.append(input, ` ${SUBJECT_NAMES[s] || s} (${count})`);
    box.appendChild(label);
  }
}

function exportBackup() {
  const blob = new Blob([JSON.stringify({ cards, settings }, null, 1)], {
    type: "application/json",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `bar-review-backup-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  $("settings-msg").textContent = "Backup saved to your downloads.";
}

async function importBackup(file) {
  try {
    const data = JSON.parse(await file.text());
    if (!data.cards || typeof data.cards !== "object") throw new Error("no cards");
    cards = data.cards;
    settings = { ...DEFAULTS, ...(data.settings || {}) };
    saveCards();
    saveSettings();
    renderSettings();
    refreshHome();
    $("settings-msg").textContent = `Restored ${Object.keys(cards).length} cards.`;
  } catch (err) {
    $("settings-msg").textContent = `That file could not be read (${err.message}).`;
  }
}

// ---------- boot ----------

async function main() {
  load();

  try {
    const res = await fetch("corpus/provisions.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    provisions = await res.json();
  } catch (err) {
    $("status").textContent =
      `Could not load the law (${err.message}). If you are offline and have ` +
      `not opened this app before, connect once and reload.`;
    $("start").hidden = true;
    return;
  }

  const manifest = await fetch("corpus/manifest.json")
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  $("about-corpus").textContent = manifest
    ? `${provisions.length} provisions from ${manifest.total} official documents. ` +
      `Coverage cut-off ${manifest.coverage_date}. Last updated ` +
      `${manifest.generated_at.slice(0, 10)}. Every card is the verbatim text of the law.`
    : `${provisions.length} provisions loaded.`;

  renderSettings();
  refreshHome();

  $("start").addEventListener("click", () => startSession(null));
  $("pick").addEventListener("click", () => {
    $("picker").hidden = !$("picker").hidden;
  });
  for (const b of document.querySelectorAll(".mode")) {
    b.addEventListener("click", () => startSession(b.dataset.subject || null));
  }
  $("reveal").addEventListener("click", revealAnswer);
  for (const b of document.querySelectorAll(".grade")) {
    b.addEventListener("click", () => gradeCard(Number(b.dataset.grade)));
  }
  $("end").addEventListener("click", finishSession);
  $("done-home").addEventListener("click", () => show("home"));

  $("nav-home").addEventListener("click", () => {
    refreshHome();
    show("home");
  });
  $("nav-library").addEventListener("click", () => show("library"));
  $("nav-settings").addEventListener("click", () => {
    renderSettings();
    show("settings");
  });

  $("q").addEventListener("input", (e) => search(e.target.value));
  $("exam-date").addEventListener("change", (e) => {
    settings.examDate = e.target.value;
    saveSettings();
    refreshHome();
  });
  $("new-limit").addEventListener("change", (e) => {
    settings.newLimit = Math.max(0, Number(e.target.value) || 0);
    saveSettings();
    refreshHome();
  });
  $("export").addEventListener("click", exportBackup);
  $("import").addEventListener("change", (e) => {
    if (e.target.files[0]) importBackup(e.target.files[0]);
  });

  document.addEventListener("keydown", (e) => {
    if ($("session").hidden) return;
    if (e.key === " " && !$("reveal").hidden) {
      e.preventDefault();
      revealAnswer();
    }
    if (["1", "2", "3"].includes(e.key)) gradeCard([0, 3, 5][Number(e.key) - 1]);
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

main();
