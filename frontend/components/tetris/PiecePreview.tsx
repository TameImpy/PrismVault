"use client";

import { useEffect, useRef } from "react";
import { PIECES, type PieceType } from "./tetris-engine";

const CELL = 22;
const PAD = 1;

interface PiecePreviewProps {
  type: PieceType | null;
  label: string;
}

export default function PiecePreview({ type, label }: PiecePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#05070a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (!type) return;

    const piece = PIECES[type];
    const shape = piece.shapes[0];
    const color = piece.color;

    // Center the piece in the 4x4 grid
    const minR = Math.min(...shape.map(([r]) => r));
    const maxR = Math.max(...shape.map(([r]) => r));
    const minC = Math.min(...shape.map(([, c]) => c));
    const maxC = Math.max(...shape.map(([, c]) => c));
    const h = maxR - minR + 1;
    const w = maxC - minC + 1;
    const offsetR = Math.floor((4 - h) / 2) - minR;
    const offsetC = Math.floor((4 - w) / 2) - minC;

    for (const [dr, dc] of shape) {
      const r = dr + offsetR;
      const c = dc + offsetC;
      const px = c * CELL;
      const py = r * CELL;

      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = 4;
      ctx.fillRect(px + PAD, py + PAD, CELL - PAD * 2, CELL - PAD * 2);
      ctx.shadowBlur = 0;

      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.fillRect(px + PAD, py + PAD, CELL - PAD * 2, 1);
    }
  }, [type]);

  return (
    <div>
      <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant mb-2 font-label">
        {label}
      </p>
      <canvas
        ref={canvasRef}
        width={4 * CELL}
        height={4 * CELL}
        className="rounded-lg"
        style={{ background: "#05070a" }}
      />
    </div>
  );
}
