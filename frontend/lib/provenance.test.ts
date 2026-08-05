import { describe, it, expect } from "vitest";
import { ProvenanceEntry, provenanceFields, provenanceFor } from "./provenance";

const SEGMENTS: ProvenanceEntry = {
  section: "Audience Segments & Reach",
  source: "data/segments.csv — the Permutive and AudienceProject extracts",
  as_at: "2026-07-21",
  coverage: "Whole network — pooled across all Immediate sites",
  period: "Rolling 90 days",
  cadence: "On request",
};

const RESEARCH: ProvenanceEntry = {
  section: "Historical Research",
  source: "Immediate Media — Travel Audience Research 2024/25",
  as_at: "",
  coverage: "",
  period: "",
  cadence: "Refreshed only when a new study is published",
};

describe("provenanceFor", () => {
  it("finds the entry for a section", () => {
    expect(provenanceFor([SEGMENTS, RESEARCH], "Historical Research")).toBe(
      RESEARCH,
    );
  });

  it("returns null for a section the brief did not render", () => {
    expect(provenanceFor([SEGMENTS], "Google Trends")).toBeNull();
  });

  it("returns null for a brief saved before provenance existed", () => {
    expect(provenanceFor(undefined, "Recommended Products")).toBeNull();
    expect(provenanceFor(null, "Recommended Products")).toBeNull();
  });
});

describe("provenanceFields", () => {
  it("labels every field, source first", () => {
    expect(provenanceFields(SEGMENTS)).toEqual([
      { label: "Source", value: SEGMENTS.source },
      { label: "As at", value: "2026-07-21" },
      { label: "Coverage", value: SEGMENTS.coverage },
      { label: "Period", value: "Rolling 90 days" },
      { label: "Refreshed", value: "On request" },
    ]);
  });

  it("omits fields with nothing behind them rather than showing a blank label", () => {
    expect(provenanceFields(RESEARCH).map((f) => f.label)).toEqual([
      "Source",
      "Refreshed",
    ]);
  });

  it("treats whitespace as nothing", () => {
    expect(
      provenanceFields({ ...RESEARCH, as_at: "   " }).map((f) => f.label),
    ).toEqual(["Source", "Refreshed"]);
  });

  it("renders nothing at all when there is no entry", () => {
    expect(provenanceFields(null)).toEqual([]);
    expect(provenanceFields(undefined)).toEqual([]);
  });
});
