/**
 * Where signing in leaves you, and what the sign-in pages owe a visitor who is
 * already signed in (#161).
 *
 * Abel reported that the browser Back button logs you out. It does not — the
 * session survives Back intact. What happens is worse for being untrue: signing
 * in navigated to the app with a *push*, so `/login` stayed in history one press
 * behind, and the login page renders its form to anyone who asks. Press Back and
 * you are looking at "Welcome back" and an empty email field, which is what
 * being logged out looks like. The next thing a user does is type their password
 * again.
 *
 * So there are two halves, and both are needed. Signing in **replaces** the
 * sign-in entry rather than stacking on it, so Back reaches the screen the user
 * was actually on before. And the sign-in pages **check for a session first**,
 * so any other route back to them — a bookmark, a typed URL, a restored tab —
 * cannot show a login form to someone who is already logged in.
 *
 * The decisions live here as plain functions taking their world as arguments,
 * the way `lib/briefDraft.ts` does, so they can be tested without a browser.
 * The pages hold the `window` and the router; this file holds the reasoning.
 */

/** Where a signed-in visitor goes when nothing else was asked for. */
export const DEFAULT_SIGNED_IN_PATH = "/app";

/** The slice of the Location API this module uses. */
export type AuthLocation = Pick<Location, "replace">;

/**
 * The return path if it is somewhere on this site, else the app.
 *
 * The path arrives in the query string (`/login?redirect=…`), which means the
 * person choosing it need not be the person following it. Only a plain absolute
 * path is honoured: `//host` and `/\host` are read by browsers as another
 * origin, and a scheme of any kind is not a path at all.
 */
export function safeReturnPath(path: string | null | undefined): string {
  if (typeof path !== "string" || path === "") return DEFAULT_SIGNED_IN_PATH;
  if (!path.startsWith("/")) return DEFAULT_SIGNED_IN_PATH;
  if (path.startsWith("//") || path.startsWith("/\\")) {
    return DEFAULT_SIGNED_IN_PATH;
  }
  return path;
}

/** What a sign-in page knows about the visitor in front of it. */
export interface AuthPageState {
  /** True while the session check is still in flight. */
  loading: boolean;
  /** True once that check has produced a user. */
  signedIn: boolean;
  /** The `redirect` query parameter, exactly as it arrived. */
  returnPath?: string | null;
}

/**
 * Where to send this visitor, or null if there is nowhere to send them.
 *
 * Null while `loading` because an unanswered check is not an answer: acting on
 * it would send away a visitor who has every right to the form. Null is not
 * "show the form", though — the page holds it back until the check settles, or
 * a signed-in user would see it flash before being redirected, which is the
 * same confusion this ticket is about, only briefer.
 */
export function signedInDestination(state: AuthPageState): string | null {
  if (state.loading) return null;
  if (!state.signedIn) return null;
  return safeReturnPath(state.returnPath);
}

/**
 * Leave the sign-in page for the app, consuming the sign-in entry.
 *
 * `replace`, never `assign` or `location.href`: this is the whole of #161. A
 * full page load is still what happens — the session cookie has just changed
 * and the server should see it — but it must not leave a login form behind.
 */
export function completeSignIn(
  location: AuthLocation,
  returnPath: string | null | undefined,
): void {
  location.replace(safeReturnPath(returnPath));
}
