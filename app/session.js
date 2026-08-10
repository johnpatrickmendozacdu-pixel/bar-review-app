// The study loop. No DOM, no storage — just what to show next and what a
// grade does.

import { AGAIN, GOOD, HARD, buildQueue, newCard, review } from "./sm2.js";

// Three self-grades, mapped onto SM-2's quality scale. A tired student at 11pm
// should not be grading themselves on a six-point scale.
export const GRADE_QUALITY = { no: AGAIN, partly: HARD, yes: GOOD };

export function startSession({ items, cards, settings, subject, now }) {
  const pool = subject
    ? items.filter((i) => i.subject === subject)
    : items.filter((i) => settings.subjects.includes(i.subject));

  const states = pool.map((i) => cards[i.id] || newCard(i.id));
  const ordered = buildQueue(states, now, settings.newLimit);

  const byId = new Map(pool.map((i) => [i.id, i]));
  return { queue: ordered.map((c) => byId.get(c.id)).filter(Boolean) };
}

export function gradeItem({ item, card, grade, now }) {
  const quality = GRADE_QUALITY[grade];
  if (quality === undefined) throw new Error(`unknown grade: ${grade}`);

  return {
    card: review(card, quality, now),
    historyEntry: { itemId: item.id, subject: item.subject, grade, at: now },
  };
}
