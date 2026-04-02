"use client";

import { useEffect, useRef } from "react";
import {
  BOARD_WIDTH,
  BOARD_HEIGHT,
  PIECES,
  getGhostPiece,
  type Board,
  type ActivePiece,
} from "./tetris-engine";

const CELL_SIZE = 28;
const PADDING = 2;

interface TetrisBoardProps {
  board: Board;
  activePiece: ActivePiece | null;
}

function drawCell(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: string,
  alpha: number = 1
) {
  const px = x * CELL_SIZE;
  const py = y * CELL_SIZE;

  ctx.globalAlpha = alpha;

  // Main fill
  ctx.fillStyle = color;
  ctx.fillRect(px + PADDING, py + PADDING, CELL_SIZE - PADDING * 2, CELL_SIZE - PADDING * 2);

  // Inner highlight (top-left bevel)
  ctx.fillStyle = "rgba(255,255,255,0.15)";
  ctx.fillRect(px + PADDING, py + PADDING, CELL_SIZE - PADDING * 2, 2);
  ctx.fillRect(px + PADDING, py + PADDING, 2, CELL_SIZE - PADDING * 2);

  // Inner shadow (bottom-right bevel)
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.fillRect(px + PADDING, py + CELL_SIZE - PADDING - 2, CELL_SIZE - PADDING * 2, 2);
  ctx.fillRect(px + CELL_SIZE - PADDING - 2, py + PADDING, 2, CELL_SIZE - PADDING * 2);

  // Glow
  ctx.shadowColor = color;
  ctx.shadowBlur = 6;
  ctx.fillStyle = color;
  ctx.fillRect(px + PADDING + 2, py + PADDING + 2, CELL_SIZE - PADDING * 2 - 4, CELL_SIZE - PADDING * 2 - 4);
  ctx.shadowBlur = 0;

  ctx.globalAlpha = 1;
}

export default function TetrisBoard({ board, activePiece }: TetrisBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = BOARD_WIDTH * CELL_SIZE;
    const height = BOARD_HEIGHT * CELL_SIZE;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Draw grid background
    ctx.fillStyle = "#05070a";
    ctx.fillRect(0, 0, width, height);

    // Grid lines (subtle)
    ctx.strokeStyle = "rgba(45, 55, 72, 0.3)";
    ctx.lineWidth = 0.5;
    for (let r = 0; r <= BOARD_HEIGHT; r++) {
      ctx.beginPath();
      ctx.moveTo(0, r * CELL_SIZE);
      ctx.lineTo(width, r * CELL_SIZE);
      ctx.stroke();
    }
    for (let c = 0; c <= BOARD_WIDTH; c++) {
      ctx.beginPath();
      ctx.moveTo(c * CELL_SIZE, 0);
      ctx.lineTo(c * CELL_SIZE, height);
      ctx.stroke();
    }

    // Draw locked cells
    for (let r = 0; r < BOARD_HEIGHT; r++) {
      for (let c = 0; c < BOARD_WIDTH; c++) {
        if (board[r][c]) {
          drawCell(ctx, c, r, board[r][c]!);
        }
      }
    }

    // Draw ghost piece
    if (activePiece) {
      const ghost = getGhostPiece(board, activePiece);
      const ghostColor = PIECES[activePiece.type].color;
      const shape = PIECES[ghost.type].shapes[ghost.rotation];
      for (const [dr, dc] of shape) {
        const r = ghost.y + dr;
        const c = ghost.x + dc;
        if (r >= 0 && r < BOARD_HEIGHT) {
          drawCell(ctx, c, r, ghostColor, 0.2);
        }
      }
    }

    // Draw active piece
    if (activePiece) {
      const color = PIECES[activePiece.type].color;
      const shape = PIECES[activePiece.type].shapes[activePiece.rotation];
      for (const [dr, dc] of shape) {
        const r = activePiece.y + dr;
        const c = activePiece.x + dc;
        if (r >= 0 && r < BOARD_HEIGHT) {
          drawCell(ctx, c, r, color);
        }
      }
    }
  }, [board, activePiece]);

  return (
    <canvas
      ref={canvasRef}
      width={BOARD_WIDTH * CELL_SIZE}
      height={BOARD_HEIGHT * CELL_SIZE}
      className="rounded-xl"
      style={{
        boxShadow: "0 0 30px rgba(0, 218, 243, 0.15), inset 0 0 20px rgba(0, 0, 0, 0.5)",
        border: "1px solid rgba(0, 218, 243, 0.2)",
      }}
    />
  );
}
