/**
 * Pure view-model helpers for the ad-format catalogue rows a brief recommended.
 *
 * The backend narrows the catalogue to exactly the formats the brief presented
 * as recommendations (synthesiser step 11) and hands the rows over verbatim.
 * Until #163 they were carried only as far as the deck; the reason a format was
 * recommended already existed in the catalogue as `best_for_brief` and simply
 * never reached the screen.
 */

/**
 * The brief heading the format reasons attach to. The model writes this
 * heading, so the literal is pinned against `SYSTEM_PROMPT` by
 * `tests/test_formats.py` — a mismatch would make the reasons vanish silently
 * rather than fail, exactly as it would for a provenance footer.
 */
export const RECOMMENDED_PRODUCTS_SECTION = "Recommended Products";

/**
 * One row of the ad-format catalogue, verbatim from the backend. Carried
 * through the deck download so CTR and viewability are placed on the slide as
 * sourced, never re-read out of the generated brief.
 */
export interface FormatRecommendation {
  format: string;
  format_family: string;
  ctr: string;
  viewability: string;
  indicative_cost: string;
  primary_objective: string;
  secondary_objective: string;
  best_for_brief: string;
  best_for_advertiser_type: string;
}

/**
 * Why this format was recommended, in one line of the planner's language.
 *
 * It is the catalogue's own `best_for_brief` text — not the objectives, and
 * never `indicative_cost`, which is model context and is deliberately kept off
 * every user-facing surface.
 */
export function formatRationale(row: FormatRecommendation): string {
  return (row?.best_for_brief || "").trim();
}

/**
 * The recommended rows that have a reason worth showing, in the order the
 * brief presented them. A row whose catalogue entry says nothing is dropped —
 * a blank line beneath a format name reads as a missing reason rather than an
 * absent one.
 */
export function rationaleRows(
  rows?: FormatRecommendation[],
): FormatRecommendation[] {
  return (rows ?? []).filter((row) => formatRationale(row) !== "");
}
