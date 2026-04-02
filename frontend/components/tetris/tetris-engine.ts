// Tetris game engine — pure functions, no React dependency.

export const BOARD_WIDTH = 10;
export const BOARD_HEIGHT = 20;

// Each cell is either null (empty) or a color string.
export type Cell = string | null;
export type Board = Cell[][];
export type PieceType = "I" | "O" | "T" | "S" | "Z" | "J" | "L";

// An active (falling) piece on the board.
export interface ActivePiece {
  type: PieceType;
  x: number;
  y: number;
  rotation: number; // 0-3
}

// Shape definition: array of [row, col] offsets from the piece origin per rotation.
export interface Piece {
  color: string;
  shapes: [number, number][][]; // 4 rotations
}

// SRS wall kick data for JLSTZ pieces (not I).
const WALL_KICKS_JLSTZ: Record<string, [number, number][]> = {
  "0>1": [[0, 0], [-1, 0], [-1, 1], [0, -2], [-1, -2]],
  "1>0": [[0, 0], [1, 0], [1, -1], [0, 2], [1, 2]],
  "1>2": [[0, 0], [1, 0], [1, -1], [0, 2], [1, 2]],
  "2>1": [[0, 0], [-1, 0], [-1, 1], [0, -2], [-1, -2]],
  "2>3": [[0, 0], [1, 0], [1, 1], [0, -2], [1, -2]],
  "3>2": [[0, 0], [-1, 0], [-1, -1], [0, 2], [-1, 2]],
  "3>0": [[0, 0], [-1, 0], [-1, -1], [0, 2], [-1, 2]],
  "0>3": [[0, 0], [1, 0], [1, 1], [0, -2], [1, -2]],
};

const WALL_KICKS_I: Record<string, [number, number][]> = {
  "0>1": [[0, 0], [-2, 0], [1, 0], [-2, -1], [1, 2]],
  "1>0": [[0, 0], [2, 0], [-1, 0], [2, 1], [-1, -2]],
  "1>2": [[0, 0], [-1, 0], [2, 0], [-1, 2], [2, -1]],
  "2>1": [[0, 0], [1, 0], [-2, 0], [1, -2], [-2, 1]],
  "2>3": [[0, 0], [2, 0], [-1, 0], [2, 1], [-1, -2]],
  "3>2": [[0, 0], [-2, 0], [1, 0], [-2, -1], [1, 2]],
  "3>0": [[0, 0], [1, 0], [-2, 0], [1, -2], [-2, 1]],
  "0>3": [[0, 0], [-1, 0], [2, 0], [-1, 2], [2, -1]],
};

// Piece definitions with SRS shapes (4 rotations each).
// Offsets are [row, col] from the piece origin.
export const PIECES: Record<PieceType, Piece> = {
  I: {
    color: "#00daf3",
    shapes: [
      [[0, 0], [0, 1], [0, 2], [0, 3]],       // 0: horizontal
      [[0, 2], [1, 2], [2, 2], [3, 2]],         // 1: vertical
      [[2, 0], [2, 1], [2, 2], [2, 3]],         // 2: horizontal (flipped)
      [[0, 1], [1, 1], [2, 1], [3, 1]],         // 3: vertical (flipped)
    ],
  },
  O: {
    color: "#f59e0b",
    shapes: [
      [[0, 0], [0, 1], [1, 0], [1, 1]],
      [[0, 0], [0, 1], [1, 0], [1, 1]],
      [[0, 0], [0, 1], [1, 0], [1, 1]],
      [[0, 0], [0, 1], [1, 0], [1, 1]],
    ],
  },
  T: {
    color: "#a855f7",
    shapes: [
      [[0, 1], [1, 0], [1, 1], [1, 2]],         // 0: T up
      [[0, 1], [1, 1], [1, 2], [2, 1]],         // 1: T right
      [[1, 0], [1, 1], [1, 2], [2, 1]],         // 2: T down
      [[0, 1], [1, 0], [1, 1], [2, 1]],         // 3: T left
    ],
  },
  S: {
    color: "#22c55e",
    shapes: [
      [[0, 1], [0, 2], [1, 0], [1, 1]],
      [[0, 0], [1, 0], [1, 1], [2, 1]],
      [[1, 1], [1, 2], [2, 0], [2, 1]],
      [[0, 0], [1, 0], [1, 1], [2, 1]],
    ],
  },
  Z: {
    color: "#ef4444",
    shapes: [
      [[0, 0], [0, 1], [1, 1], [1, 2]],
      [[0, 1], [1, 0], [1, 1], [2, 0]],
      [[1, 0], [1, 1], [2, 1], [2, 2]],
      [[0, 1], [1, 0], [1, 1], [2, 0]],
    ],
  },
  J: {
    color: "#3b82f6",
    shapes: [
      [[0, 0], [1, 0], [1, 1], [1, 2]],
      [[0, 1], [0, 2], [1, 1], [2, 1]],
      [[1, 0], [1, 1], [1, 2], [2, 2]],
      [[0, 1], [1, 1], [2, 0], [2, 1]],
    ],
  },
  L: {
    color: "#ec4899",
    shapes: [
      [[0, 2], [1, 0], [1, 1], [1, 2]],
      [[0, 1], [1, 1], [2, 1], [2, 2]],
      [[1, 0], [1, 1], [1, 2], [2, 0]],
      [[0, 0], [0, 1], [1, 1], [2, 1]],
    ],
  },
};

const ALL_TYPES: PieceType[] = ["I", "O", "T", "S", "Z", "J", "L"];

// ---------------------------------------------------------------------------
// Board
// ---------------------------------------------------------------------------

export function createBoard(): Board {
  return Array.from({ length: BOARD_HEIGHT }, () =>
    Array.from({ length: BOARD_WIDTH }, () => null)
  );
}

// ---------------------------------------------------------------------------
// Piece spawning
// ---------------------------------------------------------------------------

export function spawnPiece(type: PieceType): ActivePiece {
  return {
    type,
    x: 3, // centers most pieces on a 10-wide board
    y: 0,
    rotation: 0,
  };
}

// ---------------------------------------------------------------------------
// Collision detection
// ---------------------------------------------------------------------------

function getCells(piece: ActivePiece): [number, number][] {
  const shape = PIECES[piece.type].shapes[piece.rotation];
  return shape.map(([dr, dc]) => [piece.y + dr, piece.x + dc]);
}

export function isValidPosition(board: Board, piece: ActivePiece): boolean {
  for (const [r, c] of getCells(piece)) {
    if (c < 0 || c >= BOARD_WIDTH || r >= BOARD_HEIGHT) return false;
    // Allow rows above the board (r < 0) for spawning
    if (r >= 0 && board[r][c] !== null) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Movement
// ---------------------------------------------------------------------------

export function movePiece(
  board: Board,
  piece: ActivePiece,
  dx: number,
  dy: number
): ActivePiece | null {
  const moved: ActivePiece = { ...piece, x: piece.x + dx, y: piece.y + dy };
  return isValidPosition(board, moved) ? moved : null;
}

// ---------------------------------------------------------------------------
// Rotation (SRS with wall kicks)
// ---------------------------------------------------------------------------

export function rotatePiece(
  board: Board,
  piece: ActivePiece,
  direction: 1 | -1
): ActivePiece | null {
  const newRotation = ((piece.rotation + direction) % 4 + 4) % 4;
  const kickKey = `${piece.rotation}>${newRotation}`;
  const kicks = piece.type === "I" ? WALL_KICKS_I[kickKey] : WALL_KICKS_JLSTZ[kickKey];

  if (!kicks) return null;

  for (const [dx, dy] of kicks) {
    const candidate: ActivePiece = {
      ...piece,
      rotation: newRotation,
      x: piece.x + dx,
      y: piece.y - dy, // SRS convention: positive y = up, but our board y increases downward
    };
    if (isValidPosition(board, candidate)) return candidate;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Lock piece onto board
// ---------------------------------------------------------------------------

export function lockPiece(board: Board, piece: ActivePiece): Board {
  const newBoard = board.map((row) => [...row]);
  const color = PIECES[piece.type].color;
  for (const [r, c] of getCells(piece)) {
    if (r >= 0 && r < BOARD_HEIGHT && c >= 0 && c < BOARD_WIDTH) {
      newBoard[r][c] = color;
    }
  }
  return newBoard;
}

// ---------------------------------------------------------------------------
// Line clearing
// ---------------------------------------------------------------------------

export function clearLines(board: Board): { board: Board; linesCleared: number } {
  const remaining = board.filter((row) => row.some((cell) => cell === null));
  const linesCleared = BOARD_HEIGHT - remaining.length;
  // Prepend empty rows at top
  const emptyRows: Board = Array.from({ length: linesCleared }, () =>
    Array.from({ length: BOARD_WIDTH }, () => null)
  );
  return {
    board: [...emptyRows, ...remaining],
    linesCleared,
  };
}

// ---------------------------------------------------------------------------
// Scoring (NES-style)
// ---------------------------------------------------------------------------

const LINE_SCORES: Record<number, number> = {
  0: 0,
  1: 100,
  2: 300,
  3: 500,
  4: 800,
};

export function calculateScore(linesCleared: number, level: number): number {
  return (LINE_SCORES[linesCleared] ?? 0) * (level + 1);
}

// ---------------------------------------------------------------------------
// 7-bag random generator
// ---------------------------------------------------------------------------

export function createBag(): PieceType[] {
  const bag = [...ALL_TYPES];
  // Fisher-Yates shuffle
  for (let i = bag.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [bag[i], bag[j]] = [bag[j], bag[i]];
  }
  return bag;
}

// ---------------------------------------------------------------------------
// Hard drop
// ---------------------------------------------------------------------------

export function hardDrop(board: Board, piece: ActivePiece): ActivePiece {
  let current = piece;
  while (true) {
    const next = movePiece(board, current, 0, 1);
    if (!next) return current;
    current = next;
  }
}

// ---------------------------------------------------------------------------
// Ghost piece (for rendering preview of where piece will land)
// ---------------------------------------------------------------------------

export function getGhostPiece(board: Board, piece: ActivePiece): ActivePiece {
  return hardDrop(board, piece);
}

// ---------------------------------------------------------------------------
// Gravity speed (milliseconds per tick at each level)
// ---------------------------------------------------------------------------

export function getGravityInterval(level: number): number {
  // NES-style speed curve (approximation)
  const speeds = [800, 720, 630, 550, 470, 380, 300, 220, 140, 100];
  if (level < speeds.length) return speeds[level];
  // Cap at ~50ms for very high levels
  return Math.max(50, 100 - (level - 9) * 5);
}
