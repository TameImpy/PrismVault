## Problem Statement

The Prism Data Vault platform is a productivity tool used by a commercial advertising team, but it has no engagement or retention mechanics beyond the core insights workflow. The sales team needs a reason to return to the platform regularly and build a sense of community around it. Without a social, competitive element, the platform risks being perceived as a utility that is opened only when a brief is needed and then immediately closed.

## Solution

Add "Prism Play" — a fully playable Tetris game at `/tetris` with a shared high-score leaderboard. The game is accessible from the main navigation, styled to match the Prism Deep Sea design system, and designed to drive friendly competition among the sales team. The leaderboard uses placeholder identity (player-entered names stored in localStorage) with a `user_id: null` field so it can be wired to the authentication system being built in a separate worktree.

## User Stories

1. As a sales team member, I want to play a Tetris game within the platform, so that I have a fun reason to visit the platform beyond work tasks.
2. As a sales team member, I want to see a "Prism Play" link in the main navigation, so that I can easily discover and access the game.
3. As a player, I want to enter my name before starting a game, so that my scores are attributed to me on the leaderboard.
4. As a returning player, I want my name to be remembered between sessions, so that I don't have to re-enter it every time.
5. As a player, I want to see a splash screen with branding and the leaderboard when I arrive, so that I immediately see the competitive context before playing.
6. As a player, I want the game to use standard Tetris mechanics (7-piece bag, rotation, wall kicks, gravity, line clearing), so that it feels like a real Tetris game.
7. As a player, I want to hold a piece and swap it back later, so that I have strategic options during gameplay.
8. As a player, I want to see a preview of the next piece, so that I can plan my placements.
9. As a player, I want to hard drop pieces with the spacebar, so that I can play at speed.
10. As a player, I want the game speed to increase as I level up, so that the challenge escalates and high scores require sustained skill.
11. As a player, I want to earn more points for clearing multiple lines simultaneously (100/300/500/800), so that skilled play is rewarded.
12. As a player, I want my score to be multiplied by my current level, so that surviving at higher speeds is worth more.
13. As a player, I want to level up every 10 lines cleared, so that progression feels predictable and fair.
14. As a player, I want to see my current score, level, and lines cleared during the game, so that I can track my progress.
15. As a player, I want a visible key legend on the page, so that I know the controls without guessing.
16. As a player, I want each Tetris piece to be a distinct neon color, so that I can instantly recognise pieces during fast gameplay.
17. As a player, I want the game board and UI to match the Prism Deep Sea design system (dark theme, glass cards, cyan glow effects), so that the game feels native to the platform.
18. As a player, I want to see the top 10 leaderboard beside the game while I play, so that I'm motivated by the competition in real time.
19. As a player, I want to see my personal rank on the leaderboard even if I'm outside the top 10, so that I know where I stand and what to aim for.
20. As a player, I want a game over modal showing my final score and leaderboard position, so that I get clear closure on each run.
21. As a player, I want a "Play Again" button on the game over modal, so that I can quickly start another game.
22. As a player, I want my score automatically submitted to the shared leaderboard on game over, so that I don't have to do anything extra to compete.
23. As a future authenticated user, I want the leaderboard to support a user_id field, so that scores can be linked to real accounts when auth ships.
24. As a player on any device, I want the leaderboard to be shared across the whole team (server-stored), so that the competition is real and visible to everyone.
25. As a player, I want the page to have the standard Navbar but no Footer, so that vertical space is maximised for the game.

## Implementation Decisions

### Frontend

- **Route:** `/tetris` using Next.js app router (`frontend/app/tetris/page.tsx`).
- **Nav link:** "Prism Play" added to the Navbar between "Insights Tool" and "Resources", following existing link styling conventions. Active state uses `text-accent-cyan border-b-2 border-accent-cyan pb-1`.
- **Page layout:** Wide cinematic three-column layout. Left column: hold piece display, next piece preview, score/level/lines stats, key legend. Center: game board rendered on HTML Canvas with a Prism glow frame. Right column: leaderboard in a GlassCard. No Footer component.
- **Game engine:** Implemented as a custom React hook (`useTetris`) encapsulating all game logic — board state (10x20 grid), 7-bag random piece generation, gravity tick with speed scaling, collision detection, wall kick rotation (SRS), line clear detection, hold piece (one swap per drop), scoring, and level progression. The hook exposes a clean interface: `{board, currentPiece, nextPiece, holdPiece, score, level, lines, gameState, actions}`. This is a deep module — all logic is pure and testable without rendering.
- **Rendering:** A `TetrisBoard` component takes the board state from the hook and renders it to an HTML Canvas. Piece colors use an expanded neon palette: cyan (`#00daf3`), purple (`#a855f7`), amber (`#f59e0b`), pink (`#ec4899`), green (`#22c55e`), blue (`#3b82f6`), red (`#ef4444`). Each piece has a subtle glow effect matching the Prism Deep Sea "Data Prism Glow" pattern.
- **Controls:** Keyboard only. Arrow keys (left/right move, up rotate, down soft drop), spacebar (hard drop), shift (hold piece). A visible key legend is displayed in the left panel.
- **Game flow:** Three states — Splash (name entry + leaderboard + "Start" button), Playing (active game), Game Over (modal overlay with score, rank, "Play Again" button). Player name is persisted to localStorage and pre-filled on return visits.
- **Leaderboard component:** Fetches `GET /api/leaderboard?player_name={name}`, displays top 10 entries (rank, name, score, level) in a styled table inside a GlassCard. Shows personal rank below the table if outside top 10. Refreshes on game over.
- **Design system compliance:** All surrounding UI uses Prism Deep Sea tokens — `surface-container-lowest` for page background, `surface-container-high` for panels, glass-card for floating elements, refractive-gradient for primary buttons, backdrop-blur on the Navbar, Montserrat for headings, Inter for body text, rounded-xl corners, no 1px structural borders. Division through background color shifts per the "No-Line Rule."

### Backend

- **Leaderboard endpoints** added to `api/main.py`:
  - `GET /api/leaderboard` — query param `player_name` (optional). Returns `{top_10: [...], player_rank: int|null, total_players: int}`. Each entry: `{rank, player_name, score, lines, level, created_at}`.
  - `POST /api/leaderboard` — body `{player_name: str, score: int, lines: int, level: int, user_id: str|null}`. Validates `player_name` is non-empty and `score >= 0`. Returns the created entry with its rank.
- **Storage:** SQLite database (`data/leaderboard.db`) using Python's built-in `sqlite3` module — no additional dependencies. Single table: `scores(id, player_name, score, lines, level, user_id, created_at)`. The `user_id` column is nullable, ready for auth integration.
- **Pydantic models:** `LeaderboardSubmission` for POST validation, `LeaderboardResponse` for GET response typing.

### Scoring

- NES-style scoring: Single (1 line) = 100, Double (2 lines) = 300, Triple (3 lines) = 500, Tetris (4 lines) = 800. Each multiplied by `(level + 1)`.
- Level increases every 10 lines cleared. Gravity speed increases per level (decreasing tick interval).
- Soft drop awards 1 point per cell. Hard drop awards 2 points per cell.

### Piece Colors

| Piece | Color   | Hex       |
|-------|---------|-----------|
| I     | Cyan    | `#00daf3` |
| O     | Amber   | `#f59e0b` |
| T     | Purple  | `#a855f7` |
| S     | Green   | `#22c55e` |
| Z     | Red     | `#ef4444` |
| J     | Blue    | `#3b82f6` |
| L     | Pink    | `#ec4899` |

## Testing Decisions

### What makes a good test

Tests should verify external behavior through the public interface — the inputs and outputs of a module — not implementation details. A test should break only if the module's contract changes, not if internal logic is refactored. Each test should assert a single behavior.

### Modules to be tested

**1. Game Engine (useTetris hook logic)**
- Piece spawning: 7-bag produces all 7 pieces before repeating
- Collision detection: pieces cannot move through walls, floor, or locked pieces
- Rotation: pieces rotate correctly; wall kicks activate when rotation would collide
- Line clearing: full rows are removed, partial rows are not, rows above drop down
- Scoring: correct points for singles/doubles/triples/tetrises at various levels
- Level progression: level increments every 10 lines
- Hold piece: can hold once per drop, cannot hold again until next piece locks
- Game over: game ends when a new piece cannot spawn

**2. Leaderboard API (FastAPI endpoints)**
- `GET /api/leaderboard` returns top 10 sorted by score descending
- `GET /api/leaderboard?player_name=X` includes the player's rank when outside top 10
- `POST /api/leaderboard` creates an entry and returns it with rank
- `POST /api/leaderboard` returns 422 for missing/invalid fields (empty name, negative score)
- Leaderboard correctly handles ties (same score)
- Prior art: follows the patterns in `tests/test_api.py` — uses FastAPI `TestClient`, mocks where appropriate, one assertion per test function

## Out of Scope

- **Authentication integration** — auth is being built in a separate worktree. The `user_id` field is a nullable placeholder only.
- **Mobile/touch controls** — this is a desktop-first tool for a laptop-using sales team. No on-screen buttons or swipe gestures.
- **T-spin detection and bonus scoring** — adds implementation complexity for a mechanic most casual players won't use.
- **Multiplayer or real-time competitive play** — leaderboard is async competition only.
- **Sound effects or music** — not part of the initial build.
- **Admin controls for the leaderboard** (reset, ban, delete entries) — can be added later if needed.
- **Attract mode / demo playback** — the splash screen with the leaderboard is sufficient.
- **Footer on the Tetris page** — intentionally omitted to maximize vertical game space.

## Further Notes

- The leaderboard SQLite database should be created automatically on first request (create table if not exists).
- The `data/` directory already exists in the project root and is used for other data files (transcripts, audience CSV), so `data/leaderboard.db` is a natural location.
- The game engine hook should be structured so that the core logic (board manipulation, collision, scoring) is in pure functions that the hook calls — this makes unit testing straightforward without needing to test React hook lifecycle.
- Ghost piece (translucent preview showing where the current piece will land) should be rendered on the canvas as a quality-of-life feature — it's standard in modern Tetris and trivial to compute from the collision detection already needed.
- The leaderboard GET endpoint should support being called without a `player_name` param (returns top 10 only, no personal rank) for the splash screen before the player has entered a name.
