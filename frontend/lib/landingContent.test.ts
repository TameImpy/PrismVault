import { readFileSync } from "node:fs";
import { describe, it, expect } from "vitest";
import {
  DATA_SOURCES,
  DATA_SOURCES_HEADING,
  plainTitle,
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
   * The grid is two-up at every width, so on a phone a card holds about 98px
   * of text — ten characters of 18px Montserrat ("Historical", measured at
   * 89px, is the widest real word and fits). A longer unbreakable run leaves
   * its card, so it has to arrive carrying soft hyphens.
   */
  it("gives every title a break opportunity inside the mobile card", () => {
    const MOBILE_CARD_CHARS = 10;
    for (const source of DATA_SOURCES) {
      const runs = source.title.split(/[\s­]+/).filter(Boolean);
      for (const run of runs) {
        expect(
          run.length,
          `"${run}" in "${plainTitle(source.title)}" cannot break`,
        ).toBeLessThanOrEqual(MOBILE_CARD_CHARS);
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

  it("does not promise editorial transcripts", () => {
    expect(landingPage()).not.toMatch(/editorial transcripts/i);
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
