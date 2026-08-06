import { readFileSync } from "node:fs";
import { describe, it, expect, vi } from "vitest";
import {
  DEFAULT_DECK_FILENAME,
  DECK_ENDPOINT,
  ExportableBrief,
  deckFilename,
  deckRequestBody,
  downloadDeck,
  exportEventProps,
} from "./briefExport";

/** A brief with everything a recent run produces. Cast because the fixtures
 *  carry only the fields the export touches, not whole payloads. */
const FULL_BRIEF = {
  content: "## At a Glance\nCore Products: Homepage Takeover",
  topic: "gut health",
  advertiser: "Yakult",
  kpi: "Awareness",
  audience_segments: {
    segments: [{ segment_name: "Health Conscious", reach: 120000 }],
  },
  format_recommendations: [
    { format: "Homepage Takeover", best_for_brief: "Mass reach in a day" },
  ],
  historical_research: { title: "Gut health study 2025" },
  provenance: [
    {
      section: "Audience Segments & Reach",
      source: "Permutive",
      as_at: "2026-07-01",
      coverage: "Whole network",
      period: "Last 30 days",
    },
  ],
} as unknown as ExportableBrief;

/** A brief saved before structured segments, research and provenance existed. */
const OLD_BRIEF: ExportableBrief = {
  content: "## At a Glance\nCore Products: Newsletter",
  topic: "skincare",
  advertiser: "The Ordinary",
  kpi: "Clicks",
};

function okDeckResponse(filename = "Prism_Plan_Yakult_gut_health.pptx") {
  return {
    ok: true,
    status: 200,
    headers: {
      get: (name: string) =>
        name.toLowerCase() === "content-disposition"
          ? `attachment; filename="${filename}"`
          : null,
    },
    blob: async () => new Blob(["deck"]),
  } as unknown as Response;
}

function failedDeckResponse(detail?: string) {
  return {
    ok: false,
    status: 500,
    headers: { get: () => null },
    json: async () => {
      if (detail === undefined) throw new Error("not json");
      return { detail };
    },
  } as unknown as Response;
}

describe("deckRequestBody", () => {
  it("carries the identity of the brief being exported, never anything ambient", () => {
    // The whole point of #177: the values come from the brief passed in. A
    // handler that read the New Brief form would post whatever was typed there.
    const body = deckRequestBody(FULL_BRIEF);

    expect(body.topic).toBe("gut health");
    expect(body.advertiser).toBe("Yakult");
    expect(body.kpi).toBe("Awareness");
    expect(body.content).toBe(FULL_BRIEF.content);
  });

  it("trims the identifying fields, as the New Brief path always did", () => {
    const body = deckRequestBody({
      ...FULL_BRIEF,
      topic: "  gut health  ",
      advertiser: " Yakult ",
    });

    expect(body.topic).toBe("gut health");
    expect(body.advertiser).toBe("Yakult");
  });

  it("posts the structured payload back verbatim so the deck cannot disagree with the brief", () => {
    const body = deckRequestBody(FULL_BRIEF);

    expect(body.audience_segments).toBe(FULL_BRIEF.audience_segments);
    expect(body.format_recommendations).toBe(FULL_BRIEF.format_recommendations);
    expect(body.historical_research).toBe(FULL_BRIEF.historical_research);
    expect(body.provenance).toBe(FULL_BRIEF.provenance);
  });

  it("exports a brief saved before those features existed, thinner but valid", () => {
    // Known and accepted (#177): no backfill is possible, so the deck simply
    // comes out with fewer slides. What must not happen is a failed export.
    const body = deckRequestBody(OLD_BRIEF);

    expect(body.content).toBe(OLD_BRIEF.content);
    expect(body.advertiser).toBe("The Ordinary");
    expect(body.audience_segments).toBeUndefined();
    expect(body.format_recommendations).toBeUndefined();
    expect(body.historical_research).toBeUndefined();
    expect(body.provenance).toBeUndefined();
    // Every optional field is optional on the server too, so the posted JSON
    // is a valid request with them absent.
    expect(() => JSON.stringify(body)).not.toThrow();
  });

  it("does not vary with where the brief was opened from", () => {
    // The acceptance criterion that a deck exported from My Briefs matches the
    // one exported from the same brief freshly generated: the request body is
    // a function of the brief alone.
    expect(deckRequestBody(FULL_BRIEF)).toEqual(
      deckRequestBody({ ...FULL_BRIEF }),
    );
  });
});

describe("deckFilename", () => {
  it("uses the name the server chose", () => {
    expect(
      deckFilename('attachment; filename="Prism_Plan_Yakult_gut_health.pptx"'),
    ).toBe("Prism_Plan_Yakult_gut_health.pptx");
  });

  it("falls back when the header is missing or unparseable", () => {
    expect(deckFilename(null)).toBe(DEFAULT_DECK_FILENAME);
    expect(deckFilename("attachment")).toBe(DEFAULT_DECK_FILENAME);
  });
});

describe("exportEventProps", () => {
  it("carries the exported brief's values and where it was exported from", () => {
    expect(exportEventProps(FULL_BRIEF, "saved")).toEqual({
      topic: "gut health",
      advertiser: "Yakult",
      kpi: "Awareness",
      brief_source: "saved",
    });
  });

  it("marks a fresh run as such, so the two can be told apart later", () => {
    expect(exportEventProps(FULL_BRIEF, "new").brief_source).toBe("new");
  });
});

describe("downloadDeck", () => {
  function harness(response: Response | Error) {
    const fetchImpl = vi.fn(async (_url: string, _init: RequestInit) => {
      if (response instanceof Error) throw response;
      return response;
    });
    const saveBlob = vi.fn();
    const track = vi.fn();
    return { fetchImpl, saveBlob, track };
  }

  it("posts the brief being exported to the deck endpoint with the session cookie", async () => {
    const { fetchImpl, saveBlob, track } = harness(okDeckResponse());

    const outcome = await downloadDeck(FULL_BRIEF, "saved", {
      fetch: fetchImpl as unknown as typeof fetch,
      saveBlob,
      track,
    });

    expect(outcome).toEqual({
      ok: true,
      filename: "Prism_Plan_Yakult_gut_health.pptx",
    });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ];
    expect(url).toBe(DECK_ENDPOINT);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toMatchObject({
      topic: "gut health",
      advertiser: "Yakult",
      kpi: "Awareness",
      content: FULL_BRIEF.content,
    });
    expect(saveBlob).toHaveBeenCalledTimes(1);
    expect(saveBlob.mock.calls[0][1]).toBe("Prism_Plan_Yakult_gut_health.pptx");
  });

  it("exports the saved brief even when a different advertiser is part-typed elsewhere", async () => {
    // The specific failure #177 guards against. The function has no way to
    // reach form state — it is handed the brief — so the guard is that the
    // posted advertiser is the exported brief's whatever else is on screen.
    const { fetchImpl, saveBlob, track } = harness(okDeckResponse());

    await downloadDeck(OLD_BRIEF, "saved", {
      fetch: fetchImpl as unknown as typeof fetch,
      saveBlob,
      track,
    });

    const init = fetchImpl.mock.calls[0][1] as unknown as RequestInit;
    expect(JSON.parse(init.body as string).advertiser).toBe("The Ordinary");
  });

  it("records the click and the generated deck against the brief's own values", async () => {
    const { fetchImpl, saveBlob, track } = harness(okDeckResponse());
    let clock = 1000;

    await downloadDeck(FULL_BRIEF, "saved", {
      fetch: fetchImpl as unknown as typeof fetch,
      saveBlob,
      track,
      now: () => (clock += 500),
    });

    expect(track).toHaveBeenCalledWith("Download Deck Clicked", {
      topic: "gut health",
      advertiser: "Yakult",
      kpi: "Awareness",
      brief_source: "saved",
    });
    expect(track).toHaveBeenCalledWith("Deck Generated", {
      topic: "gut health",
      advertiser: "Yakult",
      kpi: "Awareness",
      brief_source: "saved",
      duration_ms: 500,
    });
  });

  it("reports a server failure back to the caller rather than failing silently", async () => {
    // The saved-brief view has no page-level error banner of its own, so an
    // export that fails must return something the caller can show (#177).
    const { fetchImpl, saveBlob, track } = harness(
      failedDeckResponse("Missing OPENAI_API_KEY on the server."),
    );

    const outcome = await downloadDeck(FULL_BRIEF, "saved", {
      fetch: fetchImpl as unknown as typeof fetch,
      saveBlob,
      track,
    });

    expect(outcome).toEqual({
      ok: false,
      error: "Missing OPENAI_API_KEY on the server.",
    });
    expect(saveBlob).not.toHaveBeenCalled();
    expect(track).toHaveBeenCalledWith("Deck Download Failed", {
      topic: "gut health",
      advertiser: "Yakult",
      kpi: "Awareness",
      brief_source: "saved",
      error_message: "Missing OPENAI_API_KEY on the server.",
    });
  });

  it("still says something useful when the error body is not JSON", async () => {
    const { fetchImpl, saveBlob, track } = harness(failedDeckResponse());

    const outcome = await downloadDeck(FULL_BRIEF, "new", {
      fetch: fetchImpl as unknown as typeof fetch,
      saveBlob,
      track,
    });

    expect(outcome).toEqual({ ok: false, error: "Failed to generate deck" });
  });

  it("reports a dropped connection the same way", async () => {
    const { fetchImpl, saveBlob, track } = harness(
      new Error("Failed to fetch"),
    );

    const outcome = await downloadDeck(FULL_BRIEF, "new", {
      fetch: fetchImpl as unknown as typeof fetch,
      saveBlob,
      track,
    });

    expect(outcome).toEqual({ ok: false, error: "Failed to fetch" });
    expect(saveBlob).not.toHaveBeenCalled();
  });

  it("works without an analytics sink", async () => {
    const { fetchImpl, saveBlob } = harness(okDeckResponse());

    await expect(
      downloadDeck(FULL_BRIEF, "new", {
        fetch: fetchImpl as unknown as typeof fetch,
        saveBlob,
      }),
    ).resolves.toMatchObject({ ok: true });
  });
});

/**
 * Pinned across the file boundary, as `authNavigation.test.ts` pins the rule of
 * #161. The defect in #177 was a handler that closed over New Brief form state;
 * the fix is that the only code that talks to the deck endpoint takes the brief
 * explicitly. This repo has no DOM harness to render the page and catch a
 * regression any other way.
 */
describe("the export row is fed the brief it is exporting (#177)", () => {
  function read(path: string) {
    return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
  }

  it("the app page no longer talks to the deck endpoint itself", () => {
    expect(read("app/app/page.tsx")).not.toMatch(/download-deck/);
  });

  it("both the fresh result and the saved brief render the same export row", () => {
    const page = read("app/app/page.tsx");
    expect(page).toMatch(/<BriefExportActions/);
    expect(page).toMatch(/source="new"/);
    expect(page).toMatch(/source="saved"/);
  });

  it("the export row reads the brief from its props, never from form state", () => {
    const row = read("components/BriefExportActions.tsx");
    // Its only identity fields come off `brief`; there is no local topic /
    // advertiser / kpi state for a stale value to hide in.
    expect(row).not.toMatch(/useState.*\b(topic|advertiser|kpi)\b/);
    expect(row).toMatch(/brief\.topic/);
    expect(row).toMatch(/brief\.advertiser/);
    expect(row).toMatch(/brief\.kpi/);
  });
});
