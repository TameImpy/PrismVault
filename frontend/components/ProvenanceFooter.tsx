"use client";

import {
  ProvenanceEntry,
  provenanceFields,
  provenanceFor,
} from "@/lib/provenance";

/**
 * "Where these figures come from" strip, shown once at the foot of each data
 * section of a brief (#156).
 *
 * Placed once per section rather than once per figure: a reviewer needs to
 * know which sheet a section was drawn from, when it was taken, whether it is
 * whole-network or a single site, and what period it spans. Without that, an
 * unexpected number is indistinguishable from a wrong one — during the August
 * 2026 QA round two figures were reconciled against the wrong system entirely
 * and both cost real time.
 *
 * Renders nothing when a section has no provenance, which is the case for a
 * brief saved before this existed.
 */
export default function ProvenanceFooter({
  entries,
  section,
}: {
  entries?: ProvenanceEntry[];
  section: string;
}) {
  const fields = provenanceFields(provenanceFor(entries, section));
  if (fields.length === 0) return null;

  return (
    <div className="mt-6 pt-4 border-t border-white/5">
      <p className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2">
        Where these figures come from
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        {fields.map((field) => (
          <div key={field.label} className="contents">
            <dt className="text-xs text-slate-500 whitespace-nowrap">
              {field.label}
            </dt>
            <dd className="text-xs text-on-surface-variant leading-relaxed break-words-anywhere">
              {field.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
