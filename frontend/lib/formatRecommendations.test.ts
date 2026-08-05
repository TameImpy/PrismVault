import { describe, it, expect } from "vitest";

import {
  FormatRecommendation,
  formatRationale,
  rationaleRows,
} from "./formatRecommendations";

function row(
  overrides: Partial<FormatRecommendation> = {},
): FormatRecommendation {
  return {
    format: "Standard display - MPU",
    format_family: "Standard display",
    ctr: "0.08%",
    viewability: "62%",
    indicative_cost: "£12 CPM",
    primary_objective: "Reach",
    secondary_objective: "Consideration",
    best_for_brief:
      "Efficient reach, simple messaging, and supporting display plans",
    best_for_advertiser_type: "FMCG",
    ...overrides,
  };
}

describe("formatRationale", () => {
  it("is the catalogue's own description of what the format suits", () => {
    expect(formatRationale(row())).toBe(
      "Efficient reach, simple messaging, and supporting display plans",
    );
  });

  it("never surfaces cost — indicative cost is model context, not a user-facing reason", () => {
    expect(formatRationale(row())).not.toContain("£");
  });

  it("is empty when the catalogue row has nothing to say", () => {
    expect(formatRationale(row({ best_for_brief: "" }))).toBe("");
    expect(formatRationale(row({ best_for_brief: "   " }))).toBe("");
  });
});

describe("rationaleRows", () => {
  it("keeps the recommended formats in the order the brief presented them", () => {
    const rows = [
      row({
        format: "High Impact - Parallax",
        best_for_brief: "Brand storytelling",
      }),
      row({ format: "Standard display - MPU" }),
    ];
    expect(rationaleRows(rows).map((r) => r.format)).toEqual([
      "High Impact - Parallax",
      "Standard display - MPU",
    ]);
  });

  it("drops rows with no rationale rather than rendering an empty line", () => {
    const rows = [row(), row({ format: "Podcast read", best_for_brief: "" })];
    expect(rationaleRows(rows).map((r) => r.format)).toEqual([
      "Standard display - MPU",
    ]);
  });

  it("is empty when the brief recommended nothing the catalogue recognises", () => {
    expect(rationaleRows([])).toEqual([]);
    expect(rationaleRows(undefined)).toEqual([]);
  });
});
