import { describe, it, expect } from "vitest";
import {
  PROVENANCE_SECTIONS,
  ProvenanceEntry,
  provenanceFields,
  provenanceFor,
} from "./provenance";

const SEGMENTS: ProvenanceEntry = {
  section: "Audience Segments & Reach",
  // Names the system, never a repository path — the deck's appendix carries
  // this same string to clients, and a reviewer reconciles against the export.
  source: "The Permutive segment export and the AudienceProject reach extract",
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
    expect(provenanceFor([SEGMENTS], "Recommended Products")).toBeNull();
  });

  it("passes over an entry for a section the product no longer has", () => {
    // A brief generated before Google Trends was removed (#176) still carries
    // its provenance entry, because the stored payload is the faithful record
    // of what that run produced and is never rewritten. Nothing asks for the
    // section any more, so the entry is simply never looked up — and looking
    // up the sections that remain must still work with it sitting there.
    const legacy: ProvenanceEntry = {
      section: "Google Trends",
      source: "Google Trends, queried live",
      as_at: "2026-08-05",
      coverage: "External to the network",
      period: "Rolling 12 months",
      cadence: "Queried live on every brief run",
    };
    expect(
      provenanceFor([legacy, SEGMENTS], PROVENANCE_SECTIONS.audienceSegments),
    ).toBe(SEGMENTS);
  });

  it("returns null for a brief saved before provenance existed", () => {
    expect(provenanceFor(undefined, "Recommended Products")).toBeNull();
    expect(provenanceFor(null, "Recommended Products")).toBeNull();
  });
});

describe("PROVENANCE_SECTIONS", () => {
  it("spells the names the backend registry uses", () => {
    // A typo renders nothing at all — no error, no empty box — so these are
    // pinned. data/provenance.csv is the other half of the pair, checked by
    // tests/test_provenance.py.
    expect(Object.values(PROVENANCE_SECTIONS)).toEqual([
      "Audience Segments & Reach",
      "Client Relationship",
      "Historical Research",
    ]);
  });

  it("resolves against an entry the backend produced", () => {
    expect(
      provenanceFor([SEGMENTS], PROVENANCE_SECTIONS.audienceSegments),
    ).toBe(SEGMENTS);
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
