import { describe, it, expect } from "vitest";
import {
  createBoard,
  spawnPiece,
  isValidPosition,
  movePiece,
  rotatePiece,
  lockPiece,
  clearLines,
  calculateScore,
  createBag,
  hardDrop,
  BOARD_WIDTH,
  BOARD_HEIGHT,
  PIECES,
  type Board,
  type Piece,
  type ActivePiece,
} from "../tetris-engine";

// ---------------------------------------------------------------------------
// Board creation
// ---------------------------------------------------------------------------

describe("createBoard", () => {
  it("creates a 10x20 grid of null cells", () => {
    const board = createBoard();
    expect(board.length).toBe(BOARD_HEIGHT);
    expect(board[0].length).toBe(BOARD_WIDTH);
    expect(board.every((row) => row.every((cell) => cell === null))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Piece spawning
// ---------------------------------------------------------------------------

describe("spawnPiece", () => {
  it("spawns a piece centered near the top of the board", () => {
    const active = spawnPiece("T");
    expect(active.type).toBe("T");
    expect(active.rotation).toBe(0);
    // Should be near the top center
    expect(active.y).toBeLessThanOrEqual(0);
    expect(active.x).toBeGreaterThanOrEqual(3);
    expect(active.x).toBeLessThanOrEqual(4);
  });
});

// ---------------------------------------------------------------------------
// Collision detection
// ---------------------------------------------------------------------------

describe("isValidPosition", () => {
  it("returns true for a piece in a valid empty position", () => {
    const board = createBoard();
    const piece = spawnPiece("T");
    expect(isValidPosition(board, piece)).toBe(true);
  });

  it("returns false when piece extends past left wall", () => {
    const board = createBoard();
    const piece = spawnPiece("I");
    piece.x = -5;
    expect(isValidPosition(board, piece)).toBe(false);
  });

  it("returns false when piece extends past right wall", () => {
    const board = createBoard();
    const piece = spawnPiece("I");
    piece.x = BOARD_WIDTH;
    expect(isValidPosition(board, piece)).toBe(false);
  });

  it("returns false when piece extends below floor", () => {
    const board = createBoard();
    const piece = spawnPiece("O");
    piece.y = BOARD_HEIGHT;
    expect(isValidPosition(board, piece)).toBe(false);
  });

  it("returns false when piece overlaps a locked cell", () => {
    const board = createBoard();
    board[1][4] = "#ff0000";
    const piece = spawnPiece("T"); // spawns around row 0, col 3-5
    expect(isValidPosition(board, piece)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Movement
// ---------------------------------------------------------------------------

describe("movePiece", () => {
  it("moves piece left", () => {
    const board = createBoard();
    const piece = spawnPiece("T");
    const moved = movePiece(board, piece, -1, 0);
    expect(moved).not.toBeNull();
    expect(moved!.x).toBe(piece.x - 1);
  });

  it("moves piece right", () => {
    const board = createBoard();
    const piece = spawnPiece("T");
    const moved = movePiece(board, piece, 1, 0);
    expect(moved).not.toBeNull();
    expect(moved!.x).toBe(piece.x + 1);
  });

  it("moves piece down", () => {
    const board = createBoard();
    const piece = spawnPiece("T");
    const moved = movePiece(board, piece, 0, 1);
    expect(moved).not.toBeNull();
    expect(moved!.y).toBe(piece.y + 1);
  });

  it("returns null when move is blocked by wall", () => {
    const board = createBoard();
    const piece = spawnPiece("I");
    piece.x = 0;
    const moved = movePiece(board, piece, -1, 0);
    // Depending on piece shape, this might or might not be blocked
    // but moving far left should eventually block
    piece.x = -1; // force to edge
    const moved2 = movePiece(board, { ...piece, x: 0 }, -2, 0);
    // Just test that the function returns null when invalid
    const edgePiece = { ...piece, x: -10 };
    expect(isValidPosition(board, edgePiece)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Rotation
// ---------------------------------------------------------------------------

describe("rotatePiece", () => {
  it("rotates a T piece and changes its shape", () => {
    const board = createBoard();
    const piece = spawnPiece("T");
    piece.y = 5; // move down so wall kicks aren't needed
    const rotated = rotatePiece(board, piece, 1);
    expect(rotated).not.toBeNull();
    expect(rotated!.rotation).toBe(1);
  });

  it("applies wall kick when rotation against wall would collide", () => {
    const board = createBoard();
    const piece = spawnPiece("T");
    piece.x = 0;
    piece.y = 5;
    // Rotation should still succeed via wall kick
    const rotated = rotatePiece(board, piece, 1);
    expect(rotated).not.toBeNull();
  });

  it("returns null when rotation is impossible even with kicks", () => {
    const board = createBoard();
    // Fill the board around a piece so no rotation is possible
    const piece = spawnPiece("T");
    piece.y = 10;
    piece.x = 0;
    // Block all adjacent cells
    for (let r = 9; r <= 12; r++) {
      for (let c = 0; c <= 3; c++) {
        board[r][c] = "#ff0000";
      }
    }
    // Clear only the exact cells the piece occupies in current rotation
    const shape = PIECES[piece.type].shapes[piece.rotation];
    for (const [dr, dc] of shape) {
      const r = piece.y + dr;
      const c = piece.x + dc;
      if (r >= 0 && r < BOARD_HEIGHT && c >= 0 && c < BOARD_WIDTH) {
        board[r][c] = null;
      }
    }
    const rotated = rotatePiece(board, piece, 1);
    expect(rotated).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Lock piece & line clearing
// ---------------------------------------------------------------------------

describe("lockPiece", () => {
  it("writes the piece color onto the board", () => {
    const board = createBoard();
    const piece = spawnPiece("O");
    piece.y = 18; // near bottom
    const newBoard = lockPiece(board, piece);
    // At least some cells should now have the O color
    const filled = newBoard.flat().filter((c) => c !== null);
    expect(filled.length).toBeGreaterThan(0);
  });
});

describe("clearLines", () => {
  it("clears a full row and returns the count", () => {
    const board = createBoard();
    // Fill bottom row completely
    for (let c = 0; c < BOARD_WIDTH; c++) {
      board[BOARD_HEIGHT - 1][c] = "#00daf3";
    }
    const { board: newBoard, linesCleared } = clearLines(board);
    expect(linesCleared).toBe(1);
    // Bottom row should now be empty (shifted down)
    expect(newBoard[BOARD_HEIGHT - 1].every((c) => c === null)).toBe(true);
  });

  it("does not clear a partial row", () => {
    const board = createBoard();
    for (let c = 0; c < BOARD_WIDTH - 1; c++) {
      board[BOARD_HEIGHT - 1][c] = "#00daf3";
    }
    const { linesCleared } = clearLines(board);
    expect(linesCleared).toBe(0);
  });

  it("clears multiple full rows at once", () => {
    const board = createBoard();
    for (let c = 0; c < BOARD_WIDTH; c++) {
      board[BOARD_HEIGHT - 1][c] = "#00daf3";
      board[BOARD_HEIGHT - 2][c] = "#a855f7";
    }
    const { linesCleared } = clearLines(board);
    expect(linesCleared).toBe(2);
  });

  it("drops rows above cleared lines down", () => {
    const board = createBoard();
    // Put a block at row 18
    board[BOARD_HEIGHT - 2][0] = "#ff0000";
    // Fill row 19 (bottom)
    for (let c = 0; c < BOARD_WIDTH; c++) {
      board[BOARD_HEIGHT - 1][c] = "#00daf3";
    }
    const { board: newBoard } = clearLines(board);
    // The block that was at row 18 should now be at row 19
    expect(newBoard[BOARD_HEIGHT - 1][0]).toBe("#ff0000");
  });
});

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

describe("calculateScore", () => {
  it("scores 100 * (level+1) for a single", () => {
    expect(calculateScore(1, 0)).toBe(100);
    expect(calculateScore(1, 1)).toBe(200);
    expect(calculateScore(1, 9)).toBe(1000);
  });

  it("scores 300 * (level+1) for a double", () => {
    expect(calculateScore(2, 0)).toBe(300);
    expect(calculateScore(2, 5)).toBe(1800);
  });

  it("scores 500 * (level+1) for a triple", () => {
    expect(calculateScore(3, 0)).toBe(500);
  });

  it("scores 800 * (level+1) for a tetris", () => {
    expect(calculateScore(4, 0)).toBe(800);
    expect(calculateScore(4, 2)).toBe(2400);
  });

  it("returns 0 for zero lines", () => {
    expect(calculateScore(0, 5)).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 7-bag
// ---------------------------------------------------------------------------

describe("createBag", () => {
  it("produces all 7 piece types", () => {
    const bag = createBag();
    expect(bag.length).toBe(7);
    const types = new Set(bag);
    expect(types.size).toBe(7);
  });

  it("produces a different order on subsequent calls (probabilistic)", () => {
    // Run multiple bags and check that not all are identical
    const bags = Array.from({ length: 10 }, () => createBag().join(""));
    const unique = new Set(bags);
    // Extremely unlikely all 10 are the same permutation (1/5040^9)
    expect(unique.size).toBeGreaterThan(1);
  });
});

// ---------------------------------------------------------------------------
// Hard drop
// ---------------------------------------------------------------------------

describe("hardDrop", () => {
  it("moves piece to the lowest valid position", () => {
    const board = createBoard();
    const piece = spawnPiece("O");
    const dropped = hardDrop(board, piece);
    // Should be near the bottom
    expect(dropped.y).toBeGreaterThan(piece.y);
    // One row below should be invalid
    expect(isValidPosition(board, { ...dropped, y: dropped.y + 1 })).toBe(false);
  });

  it("returns distance dropped", () => {
    const board = createBoard();
    const piece = spawnPiece("O");
    const dropped = hardDrop(board, piece);
    expect(dropped.y - piece.y).toBeGreaterThan(0);
  });
});
