import { describe, it, expect } from "vitest";

/**
 * The assistant page splits msg.content on "\n" and renders each
 * non-empty line as its own <div> inside a space-y-3 container.
 * These tests verify the split-and-filter logic.
 */
function splitLines(content: string): string[] {
  return content.split("\n");
}

function nonEmptyLines(content: string): string[] {
  return content.split("\n").filter((line) => line.trim());
}

describe("assistant message line splitting", () => {
  it("splits single-newline content into separate lines", () => {
    const input = "Line one.\nLine two.\nLine three.";
    const lines = splitLines(input);
    expect(lines).toEqual(["Line one.", "Line two.", "Line three."]);
  });

  it("preserves bold markdown within individual lines", () => {
    const input = "**Aldi shoppers**: Size 2,512,699\n**Asda shoppers**: Size 1,938,772";
    const lines = splitLines(input);
    expect(lines[0]).toBe("**Aldi shoppers**: Size 2,512,699");
    expect(lines[1]).toBe("**Asda shoppers**: Size 1,938,772");
  });

  it("double newlines produce empty lines for extra spacing", () => {
    const input = "Section one.\n\nSection two.";
    const lines = splitLines(input);
    expect(lines).toEqual(["Section one.", "", "Section two."]);
  });

  it("filters empty lines when counting visible content", () => {
    const input = "Line one.\n\n\nLine two.";
    const visible = nonEmptyLines(input);
    expect(visible).toEqual(["Line one.", "Line two."]);
  });

  it("handles empty content", () => {
    expect(splitLines("")).toEqual([""]);
    expect(nonEmptyLines("")).toEqual([]);
  });
});
