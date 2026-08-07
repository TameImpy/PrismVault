import { readFileSync } from "node:fs";
import { describe, it, expect } from "vitest";
import {
  DATA_SOURCES,
  DATA_SOURCES_HEADING,
  plainTitle,
  titleRuns,
} from "./landingContent";

const landingPage = () =>
  readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");

describe("the data sources the landing page advertises (#175)", () => {
  it("names four sources, because the heading counts them", () => {
    expect(DATA_SOURCES).toHaveLength(4);
    expect(DATA_SOURCES_HEADING).toBe("Four data sources.");
  });

  it("advertises only sources the product ships today", () => {
    expect(DATA_SOURCES.map((source) => plainTitle(source.title))).toEqual([
      "Brand Research",
      "Audience Segments & Reach",
      "Format Recommendations",
      "Campaign History & Historical Research",
    ]);
  });

  it("leaves the two surviving cards untouched", () => {
    const brandResearch = DATA_SOURCES.find(
      (source) => plainTitle(source.title) === "Brand Research",
    );
    const segments = DATA_SOURCES.find(
      (source) => plainTitle(source.title) === "Audience Segments & Reach",
    );
    expect(brandResearch?.description).toBe(
      "Automated web research into advertiser positioning, campaigns, and competitors.",
    );
    expect(segments?.description).toBe(
      "The most relevant targetable segments per platform, each with real reach.",
    );
  });

  /**
   * The grid is two-up at every width, so on a phone a card holds about 98px of
   * text, and a run that cannot break inside it leaves the card.
   *
   * This cap is a **heuristic, not a measurement**, and deliberately unlike
   * `tests/test_tile_fit.py`, which measures real Barlow advance widths because
   * the question there is whether a specific string fits a specific box. There
   * is no font-metrics harness on this side of the repo, and adding one to
   * guard four marketing titles would cost more than it protects. So: a
   * character count is not monotonic in a proportional face — "Wwwwwwwwww" is
   * far wider than "Historical" at the same ten characters — and this test can
   * be passed by a string that still overflows.
   *
   * What it is worth is the case it was written for. The cap comes from the
   * browser measurement in LESSONS_LEARNED.md: at 390px the card offers 98px,
   * where "Historical" (10 characters, 89px of 18px Montserrat) is the widest
   * real word that fits and "Recommendations" (15, 179px) is the one that did
   * not. A title arriving without break opportunities is the regression; a
   * pathological all-W title is not a thing marketing copy does.
   */
  it("gives every title a break opportunity inside the mobile card", () => {
    const WIDEST_FITTING_TITLE_RUN = "Historical".length;
    for (const source of DATA_SOURCES) {
      for (const run of titleRuns(source.title)) {
        expect(
          run.length,
          `"${run}" in "${plainTitle(source.title)}" cannot break`,
        ).toBeLessThanOrEqual(WIDEST_FITTING_TITLE_RUN);
      }
    }
  });

  /**
   * The cards sit in a two-up grid, so a description that runs long pushes its
   * card taller than the one beside it. The existing copy is the budget: the
   * two new cards may not be dramatically longer than the longest survivor.
   */
  it("keeps each description to one sentence of card-sized copy", () => {
    for (const source of DATA_SOURCES) {
      expect(source.description.length).toBeLessThanOrEqual(120);
      expect(source.description.trim().split(". ")).toHaveLength(1);
      expect(source.description.trim().endsWith(".")).toBe(true);
    }
  });
});

/**
 * Pinned by reading the page source, in the spirit of the #161 navigation pin:
 * the heading and the feature cards are JSX literals in a repo with no DOM
 * harness, so reading them is the only way to stop a removed product being
 * re-advertised by a later edit.
 */
describe("the landing page does not advertise a removed feature (#175)", () => {
  it("makes no mention of Google Trends", () => {
    expect(landingPage()).not.toMatch(/google trends/i);
    expect(landingPage()).not.toMatch(/trend data/i);
  });

  /**
   * Not scoped to a phrase, deliberately (#181). This started as a match on
   * "editorial transcripts", which passed while the page still promised
   * "editorial expertise and transcripts" in a feature card, "deep editorial
   * expertise" in the hero and "editorial insight" in the closing CTA — three
   * wordings of the one claim, none of them that phrase. A page-level promise
   * needs a page-level guard, so this matches the word: editorial is Phase 2,
   * and until it ships the marketing page may not offer it in any wording.
   *
   * The word is legitimate elsewhere in the product — the brief's Editorial
   * Insights section, the transcripts pipeline in `src/` — and this test reads
   * one file for that reason.
   */
  it("does not promise editorial, in any wording", () => {
    expect(landingPage()).not.toMatch(/editorial/i);
    expect(landingPage()).not.toMatch(/transcripts?/i);
  });

  it("drops the unified strategy claim", () => {
    expect(landingPage()).not.toMatch(/unified strategy/i);
  });

  it("renders its data source cards from the tested list", () => {
    const source = landingPage();
    expect(source).toMatch(/DATA_SOURCES/);
    expect(source).toMatch(/DATA_SOURCES_HEADING/);
  });
});
