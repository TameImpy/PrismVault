/**
 * The data sources the marketing landing page advertises.
 *
 * These live here rather than inline in the page (#175) because the list is a
 * claim about the product, not a layout detail: the heading counts the cards,
 * and every card has to name something a visitor will actually get. Editorial
 * transcripts (deferred to Phase 2) and Google Trends (removed, #176) were
 * both advertised here after they stopped being true. As data in `lib/`, the
 * claim can be tested; as JSX it could only be grepped.
 */
export interface DataSource {
  title: string;
  description: string;
}

/**
 * A soft hyphen: invisible until the browser needs to break the word, at which
 * point it renders as a hyphen at that point.
 *
 * The card grid stays two-up at every width, so on a phone a card offers about
 * 98px of text — narrower than "Recommendations" set in 18px Montserrat (179px)
 * at any font size the heading could plausibly take. The word has to break
 * somewhere. `hyphens: auto` does not do it (Chrome leaves the word overflowing
 * its card), and `overflow-wrap: break-word` alone breaks mid-syllable with no
 * hyphen — "Recomme / ndations". Marking the syllables is the one option that
 * breaks where a typesetter would, and it costs nothing at desktop width, where
 * the character is never rendered.
 */
const SHY = "­";

/** Strips the soft hyphens back out — a title's real text, for tests. */
export const plainTitle = (title: string) => title.replaceAll(SHY, "");

/**
 * The pieces a title can break into: the runs between its spaces and its soft
 * hyphens. Lives here beside `SHY` rather than in the test, so the one rule for
 * where a title may break is stated once — the character is invisible, and a
 * second copy of it in a regex is a copy no reviewer can see.
 */
export const titleRuns = (title: string) =>
  title.split(new RegExp(`[\\s${SHY}]+`)).filter(Boolean);

/**
 * The heading over the cards. It states a count, so it is only true for as
 * long as `DATA_SOURCES` has four entries — the pair is asserted together.
 */
export const DATA_SOURCES_HEADING = "Four data sources.";

export const DATA_SOURCES: DataSource[] = [
  {
    title: "Brand Research",
    description:
      "Automated web research into advertiser positioning, campaigns, and competitors.",
  },
  {
    title: "Audience Segments & Reach",
    description:
      "The most relevant targetable segments per platform, each with real reach.",
  },
  {
    title: `Format Recom${SHY}men${SHY}da${SHY}tions`,
    description:
      "Ad format benchmarks matched to the brief, naming specific products over generic advice.",
  },
  {
    title: "Campaign History & Historical Research",
    description:
      "Delivery data from the advertiser's past campaigns and comparable brands, plus matched research studies.",
  },
];
