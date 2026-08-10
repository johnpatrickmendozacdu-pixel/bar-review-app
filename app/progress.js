// Statistics derived from history. Pure functions — no storage, no DOM.

const DAY = 86400000;

// "partly" earns half credit: partial recall is real progress, and scoring it
// zero makes the number feel punitive enough to stop being useful.
const WEIGHT = { yes: 1, partly: 0.5, no: 0 };

function pct(entries) {
  if (!entries.length) return 0;
  const earned = entries.reduce((sum, e) => sum + (WEIGHT[e.grade] ?? 0), 0);
  return Math.round((earned / entries.length) * 100);
}

const dayKey = (ms) => new Date(ms).toISOString().slice(0, 10);

export function accuracy(history) {
  return pct(history);
}

export function accuracyBySubject(history) {
  const groups = {};
  for (const entry of history) {
    (groups[entry.subject] ||= []).push(entry);
  }
  return Object.fromEntries(Object.entries(groups).map(([s, e]) => [s, pct(e)]));
}

export function weakestSubject(history, minimum) {
  const groups = {};
  for (const entry of history) {
    (groups[entry.subject] ||= []).push(entry);
  }
  const eligible = Object.entries(groups).filter(([, e]) => e.length >= minimum);
  if (!eligible.length) return null;
  return eligible.sort((a, b) => pct(a[1]) - pct(b[1]))[0][0];
}

export function streakDays(history, now) {
  if (!history.length) return 0;
  const days = new Set(history.map((e) => dayKey(e.at)));

  // Start from today if studied today, otherwise yesterday — so an unfinished
  // day does not appear to break a streak that is still alive.
  let cursor = days.has(dayKey(now)) ? now : now - DAY;
  if (!days.has(dayKey(cursor))) return 0;

  let count = 0;
  while (days.has(dayKey(cursor))) {
    count++;
    cursor -= DAY;
  }
  return count;
}

export function sessionsByDay(history) {
  const groups = {};
  for (const entry of history) {
    (groups[dayKey(entry.at)] ||= []).push(entry);
  }
  return Object.entries(groups)
    .map(([day, entries]) => ({ day, count: entries.length, accuracy: pct(entries) }))
    .sort((a, b) => (a.day < b.day ? -1 : 1));
}

export function daysUntil(examDate, now) {
  return Math.max(0, Math.ceil((new Date(examDate) - now) / DAY));
}
