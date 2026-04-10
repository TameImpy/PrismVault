import { describe, it, expect } from "vitest";
import { formatAssistantMessage } from "./formatAssistantMessage";

describe("formatAssistantMessage", () => {
  it("converts single newlines between plain text to double newlines", () => {
    const input = "First paragraph.\nSecond paragraph.\nThird paragraph.";
    const result = formatAssistantMessage(input);
    expect(result).toBe("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.");
  });

  it("preserves bullet list items as separate list entries", () => {
    const input = "Here are the options:\n- Option A\n- Option B\n- Option C";
    const result = formatAssistantMessage(input);
    // Each bullet should still be on its own line, and markdown should
    // render them as a list. Double-newline between intro and first bullet is fine.
    expect(result).toContain("- Option A\n\n- Option B\n\n- Option C");
  });

  it("adds breaks between bold headers and following text", () => {
    const input = "**Permutive — Observing User Behaviour:**\nPermutive segments are built based on content.\n**Audience Project:**\nUses surveys.";
    const result = formatAssistantMessage(input);
    expect(result).toContain("**Permutive — Observing User Behaviour:**\n\nPermutive segments");
    expect(result).toContain("**Audience Project:**\n\nUses surveys.");
  });

  it("handles empty content gracefully", () => {
    expect(formatAssistantMessage("")).toBe("");
  });

  it("does not quadruple existing double newlines", () => {
    const input = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.";
    const result = formatAssistantMessage(input);
    expect(result).toBe("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.");
  });
});
