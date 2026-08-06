"use client";

import { useState } from "react";

import DraftEmailModal from "@/components/DraftEmailModal";
import WritingSamplesModal from "@/components/WritingSamplesModal";
import {
  BriefSource,
  ExportableBrief,
  downloadDeck,
  exportEventProps,
  saveBlobToDisk,
} from "@/lib/briefExport";

interface BriefExportActionsProps {
  /** The brief being exported — a fresh result or one opened from history. */
  brief: ExportableBrief;
  source: BriefSource;
  sampleCount: number;
  onSampleCountChange: (count: number) => void;
  track: (event: string, properties?: Record<string, unknown>) => void;
}

/**
 * Download Deck and Draft Email for the brief on screen.
 *
 * One component for both views, because the defect in #177 was that there were
 * two: the export row lived inside the New Brief branch, so opening a brief
 * from My Briefs offered no exports at all. Everything it needs arrives as
 * `brief` — it holds no form state and cannot reach any, which is what stops a
 * saved brief being exported under whatever advertiser happens to be typed
 * into the New Brief form.
 *
 * The error surface belongs here for the same reason. It used to sit in the
 * New Brief branch, so a failed export from a saved brief would have set an
 * error nobody could see.
 */
export default function BriefExportActions({
  brief,
  source,
  sampleCount,
  onSampleCountChange,
  track,
}: BriefExportActionsProps) {
  const [deckLoading, setDeckLoading] = useState(false);
  const [draftModalOpen, setDraftModalOpen] = useState(false);
  const [samplesModalOpen, setSamplesModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownloadDeck() {
    setDeckLoading(true);
    setError(null);
    const outcome = await downloadDeck(brief, source, {
      fetch,
      saveBlob: saveBlobToDisk,
      track,
    });
    if (!outcome.ok) setError(outcome.error);
    setDeckLoading(false);
  }

  return (
    <div className="mt-6">
      {/* An export that failed says so here, beside the button that failed. */}
      {error && (
        <div className="bg-error-container/20 border border-error/30 rounded-xl p-4 mb-4">
          <p className="text-error font-medium">{error}</p>
        </div>
      )}

      <div className="flex items-center gap-4">
        <button
          onClick={() => {
            track("Draft Email Clicked", {
              ...exportEventProps(brief, source),
              has_samples: sampleCount > 0,
              sample_count: sampleCount,
            });
            setDraftModalOpen(true);
          }}
          className="refractive-gradient px-6 py-3 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-all"
        >
          Draft Email
        </button>
        <button
          onClick={handleDownloadDeck}
          disabled={deckLoading}
          className="refractive-gradient px-6 py-3 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {deckLoading ? "Generating..." : "Download Deck"}
        </button>
        <button
          onClick={() => setSamplesModalOpen(true)}
          className="text-sm text-on-surface-variant hover:text-accent-cyan transition-colors"
        >
          Writing style: {sampleCount} sample{sampleCount !== 1 ? "s" : ""}
        </button>
      </div>

      <DraftEmailModal
        open={draftModalOpen}
        onClose={() => setDraftModalOpen(false)}
        briefContent={brief.content}
        provenance={brief.provenance}
        topic={brief.topic}
        advertiser={brief.advertiser}
        kpi={brief.kpi}
        sampleCount={sampleCount}
        onSampleCountChange={onSampleCountChange}
        // The modal's own events already carry the brief's topic, advertiser
        // and KPI from the props above; this adds where the export came from,
        // so a draft off a saved brief can be told from one off a fresh run.
        track={(event, properties) =>
          track(event, { ...properties, brief_source: source })
        }
      />

      <WritingSamplesModal
        open={samplesModalOpen}
        onClose={() => setSamplesModalOpen(false)}
        onSampleCountChange={onSampleCountChange}
        track={track}
      />
    </div>
  );
}
