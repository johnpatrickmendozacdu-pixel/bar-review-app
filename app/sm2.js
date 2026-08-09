// SM-2 spaced repetition. Pure functions, no DOM, no storage — so it can be
// tested with plain node and reasoned about in isolation.

export const MIN_EASE = 1.3;
export const DEFAULT_EASE = 2.5;

// What the three buttons mean, mapped onto SM-2's 0-5 quality scale.
// Three choices, not six: a tired student at 11pm should not be grading
// themselves on a six-point scale.
export const AGAIN = 0;
export const HARD = 3;
export const GOOD = 5;

/** A card that has never been studied. */
export function newCard(id) {
  return { id, ease: DEFAULT_EASE, interval: 0, reps: 0, due: 0, lapses: 0 };
}

/**
 * Apply a review outcome.
 * @param card  the card state
 * @param grade AGAIN | HARD | GOOD
 * @param now   epoch ms (injected so tests don't depend on the clock)
 * @returns a NEW card object; the input is not mutated
 */
export function review(card, grade, now) {
  const ease = Math.max(
    MIN_EASE,
    card.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
  );

  if (grade < HARD) {
    // Forgotten. Back to the start of the ladder, but keep the (now lower)
    // ease so repeatedly-missed cards keep coming back faster.
    return {
      ...card,
      ease,
      interval: 0,
      reps: 0,
      lapses: card.lapses + 1,
      due: now, // due again this session
    };
  }

  const reps = card.reps + 1;
  let interval;
  if (reps === 1) interval = 1;
  else if (reps === 2) interval = 6;
  else interval = Math.round(card.interval * ease);

  return {
    ...card,
    ease,
    reps,
    interval,
    due: now + interval * 86400000,
  };
}

/** Cards due now, hardest-first so the weakest material leads. */
export function dueCards(cards, now) {
  return cards
    .filter((c) => c.reps > 0 && c.due <= now)
    .sort((a, b) => a.due - b.due || a.ease - b.ease);
}

/**
 * Build a session queue: everything due, then up to `newLimit` unseen cards.
 * Due cards always come first — that is the retention engine, and burying it
 * under new material is how review apps quietly stop working.
 */
export function buildQueue(cards, now, newLimit) {
  const due = dueCards(cards, now);
  const fresh = cards.filter((c) => c.reps === 0).slice(0, newLimit);
  return [...due, ...fresh];
}
