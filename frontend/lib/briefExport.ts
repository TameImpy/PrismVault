/**
 * Exporting a brief — the deck download, and the values that identify the brief
 * being exported.
 *
 * Reported as "the export buttons disappear when you open a brief from My
 * Briefs" (#177). They were never there: the export row lived inside the New
 * Brief branch of the app page, and its download handler closed over the *form*
 * for topic, advertiser and KPI rather than over the result it was exporting.
 * Lifted into the saved-brief view unchanged it would have posted whatever
 * happened to be typed into the form — quite possibly a different advertiser —
 * alongside a saved brief's content, and the deck would come out mislabelled.
 *
 * So the export takes the brief explicitly. Everything here is a function of
 * the brief passed in and nothing else, which is what makes a deck exported
 * from My Briefs identical to one exported from the same brief freshly
 * generated, and what makes the rule testable without a browser.
 */

import type { AudienceSegmentsPayload } from "./audienceSegments";
import type { FormatRecommendation } from "./formatRecommendations";
import type { ProvenanceEntry } from "./provenance";
import type { HistoricalResearch } from "../components/HistoricalResearchCard";

export const DECK_ENDPOINT = "/api/download-deck";

/** Used when the response carries no filename of its own. */
export const DEFAULT_DECK_FILENAME = "Prism_Plan_Deck.pptx";

/**
 * A brief in a state where it can be exported, whichever surface it came from.
 *
 * The saved record and the freshly generated result carry the same synthesiser
 * payload — every brief is persisted whole — so the only assembly a caller does
 * is putting the identifying fields beside it. Everything below `kpi` is
 * optional: a brief generated before structured segments, historical research
 * or provenance existed simply exports a thinner deck (#177).
 */
export interface ExportableBrief {
  content: string;
  topic: string;
  advertiser: string;
  kpi: string;
  audience_segments?: AudienceSegmentsPayload;
  format_recommendations?: FormatRecommendation[];
  historical_research?: HistoricalResearch;
  provenance?: ProvenanceEntry[];
}

/** Where the user was standing when they exported. */
export type BriefSource = "new" | "saved";

export interface DeckRequestBody {
  content: string;
  topic: string;
  advertiser: string;
  kpi: string;
  audience_segments?: AudienceSegmentsPayload;
  format_recommendations?: FormatRecommendation[];
  historical_research?: HistoricalResearch;
  provenance?: ProvenanceEntry[];
}

/**
 * The deck request for a brief. A function of the brief alone — deliberately
 * not of where it was opened from, so the same brief exports the same deck
 * from My Briefs as it does off a fresh run.
 *
 * The structured payload is passed straight back rather than re-derived: reach
 * and CTR figures are placed on the slides as the run produced them, never
 * re-extracted from the markdown.
 */
export function deckRequestBody(brief: ExportableBrief): DeckRequestBody {
  return {
    content: brief.content,
    topic: brief.topic.trim(),
    advertiser: brief.advertiser.trim(),
    kpi: brief.kpi,
    audience_segments: brief.audience_segments,
    format_recommendations: brief.format_recommendations,
    historical_research: brief.historical_research,
    provenance: brief.provenance,
  };
}

/** The filename the server chose, or a generic one if it named none. */
export function deckFilename(contentDisposition: string | null): string {
  return (
    contentDisposition?.match(/filename="(.+)"/)?.[1] || DEFAULT_DECK_FILENAME
  );
}

/** A type alias rather than an interface, so it satisfies the analytics
 *  sink's `Record<string, unknown>` properties argument. */
export type ExportEventProps = {
  topic: string;
  advertiser: string;
  kpi: string;
  /** Whether this export came off a fresh run or a brief opened from history. */
  brief_source: BriefSource;
};

/**
 * What every export event is tagged with: the exported brief's own values —
 * not the form's — and whether it came from history, so exports off saved
 * briefs can be told from exports off fresh runs later (#177).
 */
export function exportEventProps(
  brief: ExportableBrief,
  source: BriefSource,
): ExportEventProps {
  return {
    topic: brief.topic.trim(),
    advertiser: brief.advertiser.trim(),
    kpi: brief.kpi,
    brief_source: source,
  };
}

type TrackFn = (event: string, properties?: Record<string, unknown>) => void;

export interface DownloadDeckDeps {
  fetch: typeof fetch;
  /** Hands the finished file to the user. Injected so this is testable. */
  saveBlob: (blob: Blob, filename: string) => void;
  track?: TrackFn;
  now?: () => number;
}

export type DeckDownloadOutcome =
  { ok: true; filename: string } | { ok: false; error: string };

const DECK_FAILURE_FALLBACK = "Failed to generate deck";

/**
 * Fetch the deck for a brief and hand it to the user.
 *
 * Returns the failure rather than throwing it, because both views need to put
 * it in front of the user: the saved-brief view has no error banner of its own
 * and, before #177, an export that failed there would have set an error nobody
 * could see.
 */
export async function downloadDeck(
  brief: ExportableBrief,
  source: BriefSource,
  deps: DownloadDeckDeps,
): Promise<DeckDownloadOutcome> {
  const { fetch: fetchImpl, saveBlob, track, now = Date.now } = deps;
  const eventProps = exportEventProps(brief, source);

  track?.("Download Deck Clicked", eventProps);
  const startTime = now();

  try {
    const res = await fetchImpl(DECK_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(deckRequestBody(brief)),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new Error(data?.detail || DECK_FAILURE_FALLBACK);
    }

    const blob = await res.blob();
    const filename = deckFilename(res.headers.get("content-disposition"));
    saveBlob(blob, filename);

    track?.("Deck Generated", {
      ...eventProps,
      duration_ms: now() - startTime,
    });
    return { ok: true, filename };
  } catch (err) {
    const error = err instanceof Error ? err.message : DECK_FAILURE_FALLBACK;
    track?.("Deck Download Failed", { ...eventProps, error_message: error });
    return { ok: false, error };
  }
}

/**
 * The browser's way of handing a blob to the user. Kept apart from the logic
 * above — as `draftStorage()` is in `briefDraft.ts` — so the one place that
 * touches `document` is the one place a test never needs to run.
 */
export function saveBlobToDisk(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
