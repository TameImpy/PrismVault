import { readFileSync } from "node:fs";
import { describe, it, expect, vi } from "vitest";
import {
  DEFAULT_SIGNED_IN_PATH,
  loginPath,
  safeReturnPath,
  signedInDestination,
  completeSignIn,
} from "./authNavigation";

describe("safeReturnPath", () => {
  it("keeps an ordinary in-app path", () => {
    expect(safeReturnPath("/app")).toBe("/app");
    expect(safeReturnPath("/assistant")).toBe("/assistant");
  });

  it("keeps a path with a query string and a fragment", () => {
    expect(safeReturnPath("/app?tab=mine#top")).toBe("/app?tab=mine#top");
  });

  it("falls back to the app when there is no return path", () => {
    expect(safeReturnPath(null)).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath(undefined)).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath("")).toBe(DEFAULT_SIGNED_IN_PATH);
  });

  it("refuses a path that leaves the site", () => {
    // The return path arrives in the query string, so anyone can choose it.
    expect(safeReturnPath("https://evil.example/app")).toBe(
      DEFAULT_SIGNED_IN_PATH,
    );
    expect(safeReturnPath("//evil.example/app")).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath("/\\evil.example/app")).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath("javascript:alert(1)")).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath("app")).toBe(DEFAULT_SIGNED_IN_PATH);
  });
});

describe("signedInDestination", () => {
  it("decides nothing while the session is still being checked", () => {
    expect(
      signedInDestination({
        loading: true,
        signedIn: false,
        returnPath: "/app",
      }),
    ).toBeNull();
    // Even with a user already in hand — the check is what settles `loading`.
    expect(
      signedInDestination({
        loading: true,
        signedIn: true,
        returnPath: "/app",
      }),
    ).toBeNull();
  });

  it("leaves the form alone for a visitor who is not signed in", () => {
    expect(
      signedInDestination({
        loading: false,
        signedIn: false,
        returnPath: "/app",
      }),
    ).toBeNull();
  });

  it("sends a signed-in visitor on to where they were headed (#161)", () => {
    expect(
      signedInDestination({
        loading: false,
        signedIn: true,
        returnPath: "/assistant",
      }),
    ).toBe("/assistant");
  });

  it("sends a signed-in visitor to the app when nothing was requested", () => {
    expect(
      signedInDestination({ loading: false, signedIn: true, returnPath: null }),
    ).toBe(DEFAULT_SIGNED_IN_PATH);
  });

  it("sends a signed-in visitor to the app when returnPath is omitted, not just null (signup/page.tsx never passes one)", () => {
    // signedInDestination is an optional field on AuthPageState — the signup
    // page calls this with no returnPath key at all, not an explicit null.
    // That is a different shape at the call site and deserves its own case.
    expect(signedInDestination({ loading: false, signedIn: true })).toBe(
      DEFAULT_SIGNED_IN_PATH,
    );
  });

  it("will not send a signed-in visitor off the site", () => {
    expect(
      signedInDestination({
        loading: false,
        signedIn: true,
        returnPath: "//evil.example",
      }),
    ).toBe(DEFAULT_SIGNED_IN_PATH);
  });
});

describe("completeSignIn", () => {
  it("replaces the sign-in page rather than stacking on top of it (#161)", () => {
    const location = { replace: vi.fn(), assign: vi.fn() };

    completeSignIn(location, "/app");

    // Replace is the whole fix: a pushed entry leaves the sign-in form sitting
    // one Back press behind the app, which reads as having been logged out.
    expect(location.replace).toHaveBeenCalledWith("/app");
    expect(location.assign).not.toHaveBeenCalled();
  });

  it("refuses a return path that leaves the site", () => {
    const location = { replace: vi.fn() };

    completeSignIn(location, "https://evil.example/app");

    expect(location.replace).toHaveBeenCalledWith(DEFAULT_SIGNED_IN_PATH);
  });
});

describe("safeReturnPath and the sign-in pages", () => {
  it("will not send a signed-in visitor back to a sign-in page", () => {
    // /login?redirect=/login would otherwise redirect the page onto itself.
    expect(safeReturnPath("/login")).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath("/signup")).toBe(DEFAULT_SIGNED_IN_PATH);
    expect(safeReturnPath("/login?redirect=/login")).toBe(
      DEFAULT_SIGNED_IN_PATH,
    );
  });

  it("does not mistake a path that merely starts the same way", () => {
    expect(safeReturnPath("/login-help")).toBe("/login-help");
  });
});

describe("loginPath", () => {
  it("carries the path the visitor was trying to reach", () => {
    expect(loginPath("/app")).toBe("/login?redirect=%2Fapp");
    expect(loginPath("/assistant")).toBe("/login?redirect=%2Fassistant");
  });

  it("asks for nothing in particular when there is nowhere to return to", () => {
    expect(loginPath()).toBe("/login");
    expect(loginPath(null)).toBe("/login");
    expect(loginPath("")).toBe("/login");
  });

  it("encodes the return path, as the proxy's URL builder does", () => {
    expect(loginPath("/app?tab=mine")).toBe(
      "/login?redirect=%2Fapp%3Ftab%3Dmine",
    );
  });
});

/**
 * Pinned across the file boundary, in the spirit of `tests/test_provenance.py`
 * pinning section headings against the prompt. The rule of #161 is that no
 * auth navigation may push — but the rule lives in page components this repo
 * has no DOM harness to render. Reading their source is the honest way to keep
 * a future edit from quietly reintroducing the defect.
 */
describe("no auth navigation pushes a history entry (#161)", () => {
  const PAGES = [
    "app/app/page.tsx",
    "app/assistant/page.tsx",
    "app/login/page.tsx",
    "app/signup/page.tsx",
    "app/reset-password/page.tsx",
    "contexts/AuthContext.tsx",
  ];

  for (const page of PAGES) {
    it(`${page} navigates with replace, never push`, () => {
      const source = readFileSync(
        new URL(`../${page}`, import.meta.url),
        "utf8",
      );
      expect(source).not.toMatch(/router\.push\(/);
      expect(source).not.toMatch(/window\.location\.href\s*=/);
      expect(source).not.toMatch(/location\.assign\(/);
    });
  }
});
