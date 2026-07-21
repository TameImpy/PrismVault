/**
 * Pure view-model helpers for the "Audience Segments & Reach" brief section
 * (PRD #96 / slice #99). The JSX in the brief page stays thin; all the shaping
 * and the hard rules (per-platform framing shown once, reach quoted verbatim,
 * never a summed total) live here so they can be unit-tested.
 */

export interface AudienceSegment {
  segment_name: string;
  reach: number;
  platform: string;
  category: string;
  plain_english: string;
  description: string;
  code: string;
  frequency: string;
  window: string;
}

export interface AudiencePlatform {
  platform: string;
  framing: string;
  segments: AudienceSegment[];
}

export interface AudienceSegmentsPayload {
  matched: boolean;
  note: string;
  query_terms: string[];
  platforms: AudiencePlatform[];
}

/** Format a reach count with thousands separators (e.g. 10486296 -> "10,486,296"). */
export function formatReach(reach: number): string {
  return (reach ?? 0).toLocaleString("en-GB");
}

/**
 * Platforms that actually have segments to show, in payload order. Platforms
 * with no matched segments are dropped so the UI never renders an empty card.
 */
export function visiblePlatforms(
  payload: AudienceSegmentsPayload,
): AudiencePlatform[] {
  return (payload?.platforms ?? []).filter(
    (p) => p.segments && p.segments.length > 0,
  );
}

/** True when there is nothing to show — render the honest empty state instead. */
export function isEmptyState(payload: AudienceSegmentsPayload): boolean {
  if (!payload || payload.matched === false) return true;
  return visiblePlatforms(payload).length === 0;
}

/**
 * The raw "browsed X >=2x" methodology, shown as a secondary evidence line or
 * tooltip beneath the plain-English "why". Returns "" when the methodology is
 * absent or merely repeats the plain-English headline (nothing to add).
 */
export function segmentEvidence(segment: AudienceSegment): string {
  const description = (segment.description || "").trim();
  if (!description) return "";
  if (
    description.toLowerCase() ===
    (segment.plain_english || "").trim().toLowerCase()
  ) {
    return "";
  }
  return description;
}
