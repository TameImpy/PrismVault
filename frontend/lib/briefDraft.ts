/**
 * The in-progress brief form, kept somewhere a page reload cannot reach (#160).
 *
 * Generation is the longest wait in the product, which is exactly when a user
 * reloads out of impatience — and until now everything they had typed lived
 * only in React state, so the reload took it with them.
 *
 * The store is **sessionStorage**, deliberately, not localStorage. A draft is
 * meant to outlive a reload, not the tab: a client brief is free text a planner
 * may have pasted from an email, and leaving it on disk for whoever opens the
 * browser next is not what "my form came back" is supposed to mean. Logging out
 * clears it too (`contexts/AuthContext.tsx`), so the next person to sign in on
 * the same tab does not inherit it.
 *
 * Reading and writing take the storage as an argument rather than reaching for
 * it, which keeps them testable without a browser and turns a server render —
 * where there is no storage at all — into a `null` argument rather than a
 * special case. `draftStorage()` at the foot of the file is the single place
 * that touches `window`, kept apart from the logic for exactly that reason.
 */

/** What the New Brief form holds, plus whether a run was in flight. */
export interface BriefDraft {
  topic: string;
  advertiser: string;
  kpi: string;
  clientBrief: string;
  /** Mirrors the Google Trends checkbox, which starts ticked. */
  includeTrends: boolean;
  /**
   * True while a generation is running. Persisted so that a reload mid-run can
   * say what happened rather than silently presenting a full form the user has
   * no reason to think is still waiting on anything.
   */
  generating: boolean;
}

/**
 * The form as it arrives: the version lives in the key, so a future change of
 * shape simply bumps it and leaves the old value to expire with the session.
 */
export const DRAFT_STORAGE_KEY = "prism.brief-draft.v1";

export const EMPTY_DRAFT: BriefDraft = {
  topic: "",
  advertiser: "",
  kpi: "",
  clientBrief: "",
  includeTrends: true,
  generating: false,
};

/** The slice of the Storage API this module uses. */
export type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/**
 * Whether a draft holds nothing worth restoring. An emptied form is a decision,
 * not an accident, so it is stored as *absence* — otherwise clearing the fields
 * and reloading would hand back the very input the user had just deleted.
 */
export function isEmptyDraft(draft: BriefDraft): boolean {
  return (
    draft.topic.trim() === "" &&
    draft.advertiser.trim() === "" &&
    draft.kpi.trim() === "" &&
    draft.clientBrief.trim() === "" &&
    draft.includeTrends === EMPTY_DRAFT.includeTrends
  );
}

/**
 * Whether a draft is not worth keeping at all. An empty form usually is not —
 * but an empty form with a run in flight still has something to say, because
 * the interrupted-run notice is the one thing a reload mid-generation needs.
 *
 * Read and write both ask this question, and they must not answer it
 * differently: a `readDraft` stricter than `writeDraft` would drop drafts that
 * were deliberately saved, and the reverse would keep keys nothing can restore.
 */
function isDiscardable(draft: BriefDraft): boolean {
  return isEmptyDraft(draft) && !draft.generating;
}

/** Whether two drafts hold the same input, disregarding the run flag. */
export function sameInput(a: BriefDraft, b: BriefDraft): boolean {
  return (
    a.topic === b.topic &&
    a.advertiser === b.advertiser &&
    a.kpi === b.kpi &&
    a.clientBrief === b.clientBrief &&
    a.includeTrends === b.includeTrends
  );
}

/** The stored value if it really is a string, else the form's default. */
function stringOr(value: unknown, fallback: string): string {
  return typeof value === "string" ? value : fallback;
}

/** The stored value if it really is a boolean, else the form's default. */
function booleanOr(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

/**
 * The saved draft, or null when there is none worth restoring.
 *
 * Every failure returns null rather than throwing: a corrupt value, a storage
 * that refuses to answer (Safari private browsing), or no storage at all. A
 * draft is a convenience, and no convenience should be able to stop the page
 * from rendering.
 */
export function readDraft(
  storage: DraftStorage | null | undefined,
): BriefDraft | null {
  if (!storage) return null;

  let stored: string | null;
  try {
    stored = storage.getItem(DRAFT_STORAGE_KEY);
  } catch {
    return null;
  }
  if (!stored) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(stored);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return null;
  }

  const raw = parsed as Record<string, unknown>;
  const draft: BriefDraft = {
    topic: stringOr(raw.topic, EMPTY_DRAFT.topic),
    advertiser: stringOr(raw.advertiser, EMPTY_DRAFT.advertiser),
    kpi: stringOr(raw.kpi, EMPTY_DRAFT.kpi),
    clientBrief: stringOr(raw.clientBrief, EMPTY_DRAFT.clientBrief),
    includeTrends: booleanOr(raw.includeTrends, EMPTY_DRAFT.includeTrends),
    generating: booleanOr(raw.generating, EMPTY_DRAFT.generating),
  };

  // A discardable draft restores nothing, so report it as nothing — the caller
  // then has one case to handle, not two that look the same on screen.
  return isDiscardable(draft) ? null : draft;
}

/** Save a draft, or clear the key when there is nothing left in the form. */
export function writeDraft(
  storage: DraftStorage | null | undefined,
  draft: BriefDraft,
): void {
  if (!storage) return;
  if (isDiscardable(draft)) {
    clearDraft(storage);
    return;
  }
  try {
    storage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Quota or a storage that refuses to write. The form still works; only the
    // reload safety net is lost, and saying so would help nobody mid-typing.
  }
}

/** Forget the saved draft entirely. */
export function clearDraft(storage: DraftStorage | null | undefined): void {
  if (!storage) return;
  try {
    storage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // As above — nothing the user can act on.
  }
}

/** The browser's sessionStorage, or null when there isn't one (server render). */
export function draftStorage(): DraftStorage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}
