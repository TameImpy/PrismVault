import { describe, it, expect } from "vitest";
import {
  BriefDraft,
  DRAFT_STORAGE_KEY,
  EMPTY_DRAFT,
  clearDraft,
  draftStorage,
  isEmptyDraft,
  readDraft,
  sameInput,
  writeDraft,
} from "./briefDraft";

/** A stand-in for sessionStorage — the real one is not present under vitest. */
function fakeStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
    has: (key: string) => data.has(key),
    raw: (key: string) => data.get(key) ?? null,
  };
}

/** A storage that refuses everything, as in Safari private browsing. */
const HOSTILE_STORAGE = {
  getItem() {
    throw new DOMException("denied");
  },
  setItem() {
    throw new DOMException("quota exceeded");
  },
  removeItem() {
    throw new DOMException("denied");
  },
};

const FILLED: BriefDraft = {
  topic: "gut health",
  advertiser: "Yakult",
  kpi: "Awareness",
  clientBrief: "Launching in September, 25-34 women, mid-tier budget.",
  includeTrends: false,
  generating: false,
};

describe("isEmptyDraft", () => {
  it("treats the untouched form as empty", () => {
    expect(isEmptyDraft(EMPTY_DRAFT)).toBe(true);
  });

  it("treats whitespace-only input as empty", () => {
    expect(
      isEmptyDraft({ ...EMPTY_DRAFT, topic: "   ", clientBrief: "\n" }),
    ).toBe(true);
  });

  it("counts an unticked Google Trends box as input worth keeping", () => {
    expect(isEmptyDraft({ ...EMPTY_DRAFT, includeTrends: false })).toBe(false);
  });

  it("counts the client brief alone as input worth keeping", () => {
    expect(isEmptyDraft({ ...EMPTY_DRAFT, clientBrief: "notes" })).toBe(false);
  });
});

describe("writeDraft", () => {
  it("round-trips every field, free text included", () => {
    const storage = fakeStorage();
    writeDraft(storage, FILLED);
    expect(readDraft(storage)).toEqual(FILLED);
  });

  it("records that a generation was in flight", () => {
    const storage = fakeStorage();
    writeDraft(storage, { ...FILLED, generating: true });
    expect(readDraft(storage)?.generating).toBe(true);
  });

  it("clears the key when the user empties the form, so it cannot resurrect", () => {
    const storage = fakeStorage();
    writeDraft(storage, FILLED);
    writeDraft(storage, EMPTY_DRAFT);
    expect(storage.has(DRAFT_STORAGE_KEY)).toBe(false);
    expect(readDraft(storage)).toBeNull();
  });

  it("keeps an in-flight run even if every field is blank, so clearing the form mid-generation does not lose the interrupted-run signal", () => {
    // Nothing stops a user editing the fields back to empty while a
    // generation they already started is still running (the inputs are not
    // disabled while loading). The run flag must survive that regardless.
    const storage = fakeStorage();
    const emptyButRunning: BriefDraft = { ...EMPTY_DRAFT, generating: true };
    writeDraft(storage, emptyButRunning);
    expect(storage.has(DRAFT_STORAGE_KEY)).toBe(true);
    expect(readDraft(storage)).toEqual(emptyButRunning);
  });

  it("clears the key once that run ends and the form is still empty", () => {
    const storage = fakeStorage();
    writeDraft(storage, { ...EMPTY_DRAFT, generating: true });
    writeDraft(storage, { ...EMPTY_DRAFT, generating: false });
    expect(storage.has(DRAFT_STORAGE_KEY)).toBe(false);
    expect(readDraft(storage)).toBeNull();
  });

  it("survives a storage that refuses to write", () => {
    expect(() => writeDraft(HOSTILE_STORAGE, FILLED)).not.toThrow();
  });

  it("does nothing when there is no storage at all (server render)", () => {
    expect(() => writeDraft(null, FILLED)).not.toThrow();
  });
});

describe("readDraft", () => {
  it("returns null when nothing was ever saved", () => {
    expect(readDraft(fakeStorage())).toBeNull();
  });

  it("returns null when there is no storage at all (server render)", () => {
    expect(readDraft(null)).toBeNull();
  });

  it("returns null rather than throwing on unreadable storage", () => {
    expect(readDraft(HOSTILE_STORAGE)).toBeNull();
  });

  it("returns null on a corrupt value instead of crashing the page", () => {
    expect(
      readDraft(fakeStorage({ [DRAFT_STORAGE_KEY]: "{not json" })),
    ).toBeNull();
  });

  it("returns null on a value of the wrong shape", () => {
    expect(
      readDraft(fakeStorage({ [DRAFT_STORAGE_KEY]: '"a string"' })),
    ).toBeNull();
    expect(readDraft(fakeStorage({ [DRAFT_STORAGE_KEY]: "null" }))).toBeNull();
    expect(readDraft(fakeStorage({ [DRAFT_STORAGE_KEY]: "[]" }))).toBeNull();
  });

  it("fills in fields a stored draft is missing rather than dropping it", () => {
    const storage = fakeStorage({
      [DRAFT_STORAGE_KEY]: JSON.stringify({ advertiser: "Yakult" }),
    });
    expect(readDraft(storage)).toEqual({
      ...EMPTY_DRAFT,
      advertiser: "Yakult",
    });
  });

  it("ignores fields of the wrong type", () => {
    const storage = fakeStorage({
      [DRAFT_STORAGE_KEY]: JSON.stringify({
        topic: 42,
        includeTrends: "yes",
        advertiser: "Yakult",
      }),
    });
    expect(readDraft(storage)).toEqual({
      ...EMPTY_DRAFT,
      advertiser: "Yakult",
    });
  });

  it("ignores a generating flag of the wrong type rather than wrongly showing an interrupted run", () => {
    const storage = fakeStorage({
      [DRAFT_STORAGE_KEY]: JSON.stringify({
        advertiser: "Yakult",
        generating: "yes",
      }),
    });
    expect(readDraft(storage)).toEqual({
      ...EMPTY_DRAFT,
      advertiser: "Yakult",
    });
  });

  it("returns null when every field was junk, leaving nothing to restore", () => {
    const storage = fakeStorage({
      [DRAFT_STORAGE_KEY]: JSON.stringify({ topic: 42, includeTrends: "yes" }),
    });
    expect(readDraft(storage)).toBeNull();
  });

  it("returns null for a stored draft with nothing in it", () => {
    const storage = fakeStorage({
      [DRAFT_STORAGE_KEY]: JSON.stringify(EMPTY_DRAFT),
    });
    expect(readDraft(storage)).toBeNull();
  });
});

describe("clearDraft", () => {
  it("removes a saved draft", () => {
    const storage = fakeStorage();
    writeDraft(storage, FILLED);
    clearDraft(storage);
    expect(readDraft(storage)).toBeNull();
  });

  it("survives a storage that refuses to delete", () => {
    expect(() => clearDraft(HOSTILE_STORAGE)).not.toThrow();
    expect(() => clearDraft(null)).not.toThrow();
  });
});

describe("sameInput", () => {
  it("ignores whether a generation was running", () => {
    expect(sameInput(FILLED, { ...FILLED, generating: true })).toBe(true);
  });

  it("notices an edit to any field", () => {
    expect(sameInput(FILLED, { ...FILLED, topic: "skincare" })).toBe(false);
    expect(sameInput(FILLED, { ...FILLED, advertiser: "The Ordinary" })).toBe(
      false,
    );
    expect(sameInput(FILLED, { ...FILLED, kpi: "Clicks" })).toBe(false);
    expect(sameInput(FILLED, { ...FILLED, clientBrief: "" })).toBe(false);
    expect(sameInput(FILLED, { ...FILLED, includeTrends: true })).toBe(false);
  });
});

describe("draftStorage", () => {
  it("returns null rather than throwing when there is no window, as under this test runner and during a server render", () => {
    // vitest here runs in the node environment (no jsdom, per repo
    // convention) — `window` is genuinely undefined, so this exercises the
    // exact SSR branch the doc comment on draftStorage() describes, not a
    // simulation of it.
    expect(() => draftStorage()).not.toThrow();
    expect(draftStorage()).toBeNull();
  });
});
