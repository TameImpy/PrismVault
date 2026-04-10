/**
 * Preprocess LLM output so single newlines render as paragraph breaks
 * in markdown. Replaces lone \n with \n\n while preserving existing
 * double newlines.
 */
export function formatAssistantMessage(content: string): string {
  // First, normalise existing double newlines to a placeholder
  // Then convert remaining single newlines to doubles
  // Then restore the originals
  return content
    .replace(/\n\n/g, "\x00")
    .replace(/\n/g, "\n\n")
    .replace(/\x00/g, "\n\n");
}
