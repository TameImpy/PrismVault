/**
 * Preprocess LLM output so single newlines render as visible breaks
 * in markdown. Appends two trailing spaces before each \n to create
 * a markdown hard line break, and preserves existing double newlines
 * as paragraph breaks.
 */
export function formatAssistantMessage(content: string): string {
  return content
    // Preserve existing paragraph breaks (double newlines)
    .replace(/\n\n/g, "\x00")
    // Convert single newlines to markdown hard breaks (two trailing spaces + newline)
    .replace(/\n/g, "  \n")
    // Restore paragraph breaks
    .replace(/\x00/g, "\n\n");
}
