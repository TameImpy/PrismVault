"use client";

import {
  FormatRecommendation,
  RECOMMENDED_PRODUCTS_SECTION,
  formatRationale,
  rationaleRows,
} from "@/lib/formatRecommendations";

/**
 * "Why these formats" strip, shown once at the foot of the brief's Recommended
 * Products section (#163).
 *
 * The reason is the catalogue's own `best_for_brief` text, placed here rather
 * than written by the model — the same rule the provenance footer follows, and
 * for the same reason: a reason that is generated alongside the recommendation
 * can drift from it, and a reason that cannot be trusted is worse than none.
 * The rows are the ones the synthesiser already narrowed to the formats this
 * brief actually recommended, so a format named only in passing never appears.
 *
 * It sits below the list rather than inside it because `SYSTEM_PROMPT` bans a
 * per-format rationale line in the prose (each entry shows exactly four
 * fields) and closes the section with one combined rationale instead. That
 * discipline is deliberate and is left intact: the per-format reason arrives
 * as a separate strip, so #163 is answered without the list growing a fifth
 * field the model would have to be trusted to fill.
 *
 * Renders nothing outside that section, and nothing when no recommended format
 * matched the catalogue — which is the case for a brief saved before this
 * existed, and for one whose recommendations the name guardrail did not
 * recognise.
 */
export default function FormatRationale({
  rows,
  section,
}: {
  rows?: FormatRecommendation[];
  section: string;
}) {
  if (section !== RECOMMENDED_PRODUCTS_SECTION) return null;

  const recommended = rationaleRows(rows);
  if (recommended.length === 0) return null;

  return (
    <div className="mt-6 pt-4 border-t border-white/5">
      <p className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2">
        Why these formats
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        {recommended.map((row) => (
          <div key={row.format} className="contents">
            <dt className="text-xs text-on-surface font-medium whitespace-nowrap">
              {row.format}
            </dt>
            <dd className="text-xs text-on-surface-variant leading-relaxed break-words-anywhere">
              {formatRationale(row)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
