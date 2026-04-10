import { describe, it, expect } from "vitest";
import { formatAssistantMessage } from "./formatAssistantMessage";

describe("formatAssistantMessage", () => {
  it("converts single newlines to markdown hard breaks (two trailing spaces)", () => {
    const input = "First line.\nSecond line.\nThird line.";
    const result = formatAssistantMessage(input);
    expect(result).toBe("First line.  \nSecond line.  \nThird line.");
  });

  it("preserves existing double newlines as paragraph breaks", () => {
    const input = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.";
    const result = formatAssistantMessage(input);
    expect(result).toBe("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.");
  });

  it("handles mixed single and double newlines", () => {
    const input = "Intro line.\nDetail line.\n\nNew section.\nMore detail.";
    const result = formatAssistantMessage(input);
    expect(result).toBe("Intro line.  \nDetail line.\n\nNew section.  \nMore detail.");
  });

  it("adds hard breaks between bold headers and following text", () => {
    const input = "**Permutive:**\nBuilt on browsing.\n**Audience Project:**\nUses surveys.";
    const result = formatAssistantMessage(input);
    expect(result).toContain("**Permutive:**  \nBuilt on browsing.");
    expect(result).toContain("**Audience Project:**  \nUses surveys.");
  });

  it("handles empty content gracefully", () => {
    expect(formatAssistantMessage("")).toBe("");
  });
});
