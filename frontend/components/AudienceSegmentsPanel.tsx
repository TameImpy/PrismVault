"use client";

import CollapsiblePanel from "@/components/CollapsiblePanel";
import ProvenanceFooter from "@/components/ProvenanceFooter";
import {
  AudienceSegmentsPayload,
  formatReach,
  isEmptyState,
  segmentEvidence,
  visiblePlatforms,
} from "@/lib/audienceSegments";
import { PROVENANCE_SECTIONS, ProvenanceEntry } from "@/lib/provenance";

/**
 * "Audience Segments & Reach" brief section (PRD #96 / slice #99).
 *
 * Renders the deterministic audience_segments payload as two stacked
 * per-platform cards. Hard rules enforced here and in lib/audienceSegments:
 * per-platform framing is shown once as a card header (never per row); the
 * plain-English "why" is the headline with the raw methodology as secondary
 * evidence; reach is quoted verbatim; and there is NEVER a summed total — a
 * visible note says so because segments overlap and are not de-duplicated.
 *
 * The reach figures live here, so the source line does too (#156). The brief's
 * "Audience Segments & Reach" prose card carries the same footer: this is the
 * one place the same section states its provenance twice, and deliberately —
 * a reviewer reconciling a reach number is reading this table, and sending
 * them to another card to find out which export it came from is the gap the
 * ticket was raised about.
 */
export default function AudienceSegmentsPanel({
  data,
  provenance,
}: {
  data?: AudienceSegmentsPayload;
  provenance?: ProvenanceEntry[];
}) {
  if (!data) return null;

  return (
    <CollapsiblePanel title="Audience Segments & Reach" defaultOpen={false}>
      {isEmptyState(data) ? (
        <>
          <p className="text-on-surface-variant text-sm leading-relaxed">
            No strongly-matched audience segments were found for this brief.
          </p>
          {/* An absence is only worth trusting when you can see what was
              searched, so the empty state names the catalogue too. */}
          <ProvenanceFooter
            entries={provenance}
            section={PROVENANCE_SECTIONS.audienceSegments}
          />
        </>
      ) : (
        <div className="space-y-5">
          {/* Never-sum note — reach must never be totalled across segments. */}
          <div className="flex items-start gap-2 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3">
            <span aria-hidden className="text-accent">
              &#9888;
            </span>
            <p className="text-on-surface-variant text-xs leading-relaxed">
              Reach is shown per segment. Don&rsquo;t add these figures together
              &mdash; segments overlap and are not de-duplicated, so no combined
              total is meaningful.
            </p>
          </div>

          {visiblePlatforms(data).map((platform) => (
            <div
              key={platform.platform}
              className="rounded-2xl border border-white/10 bg-surface-container-lowest overflow-hidden"
            >
              {/* Framing shown once, as the card header. */}
              <div className="px-4 py-3 border-b border-white/10">
                <span className="font-headline font-bold text-on-surface">
                  {platform.platform}
                </span>
                <span className="text-on-surface-variant text-xs ml-2">
                  {platform.framing}
                </span>
              </div>

              <ul className="divide-y divide-white/5">
                {platform.segments.map((segment) => {
                  const evidence = segmentEvidence(segment);
                  return (
                    <li
                      key={`${segment.platform}-${segment.code}-${segment.segment_name}`}
                      className="flex items-start justify-between gap-4 px-4 py-3"
                    >
                      <div className="min-w-0">
                        {/* Plain-English "why" is the headline. */}
                        <p className="text-on-surface text-sm font-medium">
                          {segment.plain_english || segment.segment_name}
                        </p>
                        {/* Raw methodology as secondary evidence; code tucked into the title. */}
                        {evidence && (
                          <p
                            className="text-on-surface-variant text-xs mt-0.5 leading-relaxed"
                            title={
                              segment.code
                                ? `Ad-ops code: ${segment.code}`
                                : undefined
                            }
                          >
                            {segment.segment_name} &middot; {evidence}
                          </p>
                        )}
                      </div>
                      {/* Reach quoted verbatim as a chip. */}
                      <span className="shrink-0 rounded-full bg-surface-container-highest text-accent text-xs font-medium px-3 py-1 tabular-nums">
                        {formatReach(segment.reach)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}

          <ProvenanceFooter
            entries={provenance}
            section={PROVENANCE_SECTIONS.audienceSegments}
          />
        </div>
      )}
    </CollapsiblePanel>
  );
}
