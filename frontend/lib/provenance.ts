/**
 * Pure view-model helpers for the data-provenance strip shown under each data
 * section of a brief (#156).
 *
 * The backend decides *what* a section's provenance is (src/provenance.py) —
 * these helpers only decide how it reads. The rule the JSX must not be allowed
 * to break: a field with nothing behind it is left out entirely, never rendered
 * as a label with a blank after it. "As at:" followed by nothing states less
 * than saying nothing at all, and this whole feature exists so a reviewer can
 * tell an out-of-date figure from a differently-defined one.
 */

/** One data section's provenance, verbatim from the brief payload. */
export interface ProvenanceEntry {
  section: string;
  source: string;
  as_at: string;
  coverage: string;
  period: string;
  cadence: string;
}

export interface ProvenanceField {
  label: string;
  value: string;
}

/**
 * Section names that a surface has to name as a literal, because it has no
 * markdown heading to read one from. A typo here renders nothing at all — no
 * error, no empty box — so the names live in one place and
 * `tests/test_provenance.py` checks the registry still carries them.
 */
export const PROVENANCE_SECTIONS = {
  audienceSegments: "Audience Segments & Reach",
  clientRelationship: "Client Relationship",
  historicalResearch: "Historical Research",
} as const;

/** Field render order — source first, because it is the question people ask. */
const FIELD_LABELS: [keyof ProvenanceEntry, string][] = [
  ["source", "Source"],
  ["as_at", "As at"],
  ["coverage", "Coverage"],
  ["period", "Period"],
  ["cadence", "Refreshed"],
];

/**
 * The provenance for one section, or null when there is none. Briefs saved
 * before provenance existed carry no entries at all, which is why the list is
 * optional rather than assumed.
 *
 * The reverse also happens: a brief saved before Google Trends was removed
 * (#176) carries an entry for a section nothing renders any more. Lookup is by
 * name, so that entry is simply never asked for — the stored payload stays the
 * faithful record of what its run produced rather than being rewritten to
 * match today's feature set.
 */
export function provenanceFor(
  entries: ProvenanceEntry[] | undefined | null,
  section: string,
): ProvenanceEntry | null {
  if (!entries) return null;
  return entries.find((entry) => entry.section === section) ?? null;
}

/** The populated fields of an entry, labelled, in render order. */
export function provenanceFields(
  entry: ProvenanceEntry | null | undefined,
): ProvenanceField[] {
  if (!entry) return [];
  return FIELD_LABELS.filter(([key]) => (entry[key] ?? "").trim() !== "").map(
    ([key, label]) => ({ label, value: entry[key].trim() }),
  );
}
