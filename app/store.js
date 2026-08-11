// All persistence lives here. Storage is injected so this is testable in node
// and swappable if localStorage is ever outgrown.
// ponytail: localStorage. Progress is kilobytes; move to IndexedDB only if it
// approaches the ~5MB cap.

const KEYS = {
  cards: "barrev.cards",
  notes: "barrev.notes",
  settings: "barrev.settings",
  history: "barrev.history",
};

export const DEFAULT_SETTINGS = {
  examDate: "2026-09-06",
  newLimit: 20,
  subjects: ["civil", "criminal", "political", "commercial_tax", "labor", "remedial"],
};

function readJson(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

export function createStore(storage) {
  const write = (key, value) => storage.setItem(key, JSON.stringify(value));

  return {
    getCards: () => readJson(storage, KEYS.cards, {}),

    setCard(card) {
      const cards = this.getCards();
      cards[card.id] = card;
      write(KEYS.cards, cards);
    },

    allNotes: () => readJson(storage, KEYS.notes, {}),

    getNote(refId) {
      return this.allNotes()[refId] || "";
    },

    setNote(refId, text) {
      const notes = this.allNotes();
      if (!text || !text.trim()) delete notes[refId];
      else notes[refId] = text;
      write(KEYS.notes, notes);
    },

    getSettings: () => ({
      ...DEFAULT_SETTINGS,
      ...readJson(storage, KEYS.settings, {}),
    }),

    setSettings(partial) {
      write(KEYS.settings, { ...this.getSettings(), ...partial });
    },

    getHistory: () => readJson(storage, KEYS.history, []),

    appendHistory(entry) {
      const history = this.getHistory();
      history.push(entry);
      write(KEYS.history, history);
    },

    exportAll() {
      return {
        version: 1,
        cards: this.getCards(),
        notes: this.allNotes(),
        settings: this.getSettings(),
        history: this.getHistory(),
      };
    },

    importAll(data) {
      if (!data || typeof data !== "object" || !data.cards || typeof data.cards !== "object") {
        throw new Error("That file is not a Bar Review backup.");
      }
      write(KEYS.cards, data.cards);
      write(KEYS.notes, data.notes || {});
      write(KEYS.settings, { ...DEFAULT_SETTINGS, ...(data.settings || {}) });
      write(KEYS.history, Array.isArray(data.history) ? data.history : []);
    },
  };
}
