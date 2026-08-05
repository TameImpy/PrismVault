import { describe, it, expect } from "vitest";

import {
  formatReach,
  visiblePlatforms,
  isEmptyState,
  segmentEvidence,
  segmentMatchReason,
  AudienceSegmentsPayload,
  AudienceSegment,
} from "./audienceSegments";

function segment(overrides: Partial<AudienceSegment> = {}): AudienceSegment {
  return {
    segment_name: "Baking Fans",
    reach: 2282660,
    platform: "Permutive",
    category: "Food & Drink",
    plain_english: "Regularly browses baking content",
    description: "browsed for baking content at least 2 times",
    code: "101",
    frequency: "R",
    window: "90 Days",
    match_reason: "Matched on: baking, cake",
    ...overrides,
  };
}

function payload(
  overrides: Partial<AudienceSegmentsPayload> = {},
): AudienceSegmentsPayload {
  return {
    matched: true,
    note: "Reach figures are per-segment and must not be summed.",
    query_terms: ["baking"],
    platforms: [
      {
        platform: "AP",
        framing: "Modelled first-party audience — broad reach",
        segments: [
          {
            segment_name: "Confident bakers",
            reach: 10486296,
            platform: "AP",
            category: "Food & Drink",
            plain_english: "Feel confident when baking",
            description: "",
            code: "ap_x 1",
            frequency: "",
            window: "",
          },
        ],
      },
      {
        platform: "Permutive",
        framing: "Behavioural — recently engaged browsers",
        segments: [],
      },
    ],
    ...overrides,
  };
}

describe("formatReach", () => {
  it("formats a reach count with thousands separators", () => {
    expect(formatReach(10486296)).toBe("10,486,296");
    expect(formatReach(940120)).toBe("940,120");
    expect(formatReach(0)).toBe("0");
  });
});

describe("visiblePlatforms", () => {
  it("returns only platforms that have segments, preserving order", () => {
    const visible = visiblePlatforms(payload());
    expect(visible.map((p) => p.platform)).toEqual(["AP"]);
  });

  it("returns nothing when no platform has segments", () => {
    const empty = payload({
      platforms: [
        { platform: "AP", framing: "x", segments: [] },
        { platform: "Permutive", framing: "y", segments: [] },
      ],
    });
    expect(visiblePlatforms(empty)).toEqual([]);
  });
});

describe("segmentEvidence", () => {
  it("returns the raw methodology as secondary evidence", () => {
    expect(segmentEvidence(segment())).toBe(
      "browsed for baking content at least 2 times",
    );
  });

  it("is empty when the methodology just repeats the plain-English headline", () => {
    const s = segment({
      plain_english: "Buy baking ingredients",
      description: "Buy baking ingredients",
    });
    expect(segmentEvidence(s)).toBe("");
  });

  it("is empty when there is no description", () => {
    expect(segmentEvidence(segment({ description: "" }))).toBe("");
  });
});

describe("segmentMatchReason", () => {
  it("carries the backend's line through verbatim", () => {
    expect(segmentMatchReason(segment())).toBe("Matched on: baking, cake");
  });

  it("is empty for a brief saved before match reasons existed", () => {
    // The field is optional on the wire — an older saved brief has no reason
    // and must render the segment without one, not the string "undefined".
    const { match_reason, ...older } = segment();
    expect(segmentMatchReason(older as AudienceSegment)).toBe("");
  });

  it("is empty when the backend had nothing to say", () => {
    expect(segmentMatchReason(segment({ match_reason: "   " }))).toBe("");
  });
});
