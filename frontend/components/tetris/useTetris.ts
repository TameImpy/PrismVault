"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createBoard,
  createBag,
  spawnPiece,
  isValidPosition,
  movePiece,
  rotatePiece,
  lockPiece,
  clearLines,
  calculateScore,
  hardDrop,
  getGravityInterval,
  type Board,
  type ActivePiece,
  type PieceType,
} from "./tetris-engine";

export type GameState = "idle" | "playing" | "gameOver";

export interface TetrisState {
  board: Board;
  activePiece: ActivePiece | null;
  nextPiece: PieceType;
  holdPiece: PieceType | null;
  canHold: boolean;
  score: number;
  level: number;
  lines: number;
  gameState: GameState;
}

export interface TetrisActions {
  start: () => void;
  moveLeft: () => void;
  moveRight: () => void;
  softDrop: () => void;
  hardDropAction: () => void;
  rotate: () => void;
  hold: () => void;
}

function nextFromBag(bag: PieceType[]): { type: PieceType; bag: PieceType[] } {
  if (bag.length === 0) bag = createBag();
  const [type, ...rest] = bag;
  return { type, bag: rest };
}

export function useTetris(): TetrisState & { actions: TetrisActions } {
  const [board, setBoard] = useState<Board>(createBoard);
  const [activePiece, setActivePiece] = useState<ActivePiece | null>(null);
  const [nextPieceType, setNextPieceType] = useState<PieceType>("T");
  const [holdPieceType, setHoldPieceType] = useState<PieceType | null>(null);
  const [canHold, setCanHold] = useState(true);
  const [score, setScore] = useState(0);
  const [level, setLevel] = useState(0);
  const [lines, setLines] = useState(0);
  const [gameState, setGameState] = useState<GameState>("idle");

  const bagRef = useRef<PieceType[]>([]);
  const gravityRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Refs mirroring state for use inside callbacks without stale closures
  const boardRef = useRef(board);
  const activePieceRef = useRef(activePiece);
  const scoreRef = useRef(score);
  const levelRef = useRef(level);
  const linesRef = useRef(lines);
  const canHoldRef = useRef(canHold);
  const gameStateRef = useRef(gameState);

  boardRef.current = board;
  activePieceRef.current = activePiece;
  scoreRef.current = score;
  levelRef.current = level;
  linesRef.current = lines;
  canHoldRef.current = canHold;
  gameStateRef.current = gameState;

  const spawnNext = useCallback((overrideType?: PieceType) => {
    let type: PieceType;
    if (overrideType) {
      type = overrideType;
    } else {
      const result = nextFromBag(bagRef.current);
      type = result.type;
      bagRef.current = result.bag;
    }

    // Prepare the next-next piece
    const nn = nextFromBag(bagRef.current);
    bagRef.current = nn.bag;
    setNextPieceType(nn.type);

    const piece = spawnPiece(type);
    if (!isValidPosition(boardRef.current, piece)) {
      setGameState("gameOver");
      setActivePiece(null);
      return;
    }
    setActivePiece(piece);
    setCanHold(true);
  }, []);

  const lockAndClear = useCallback(() => {
    const piece = activePieceRef.current;
    if (!piece) return;

    const locked = lockPiece(boardRef.current, piece);
    const { board: clearedBoard, linesCleared } = clearLines(locked);
    setBoard(clearedBoard);

    if (linesCleared > 0) {
      const newLines = linesRef.current + linesCleared;
      const newLevel = Math.floor(newLines / 10);
      const pts = calculateScore(linesCleared, levelRef.current);
      setLines(newLines);
      setLevel(newLevel);
      setScore((s) => s + pts);
    }

    // Spawn next piece using the already-queued next piece
    const type = nextPieceType;
    const nn = nextFromBag(bagRef.current);
    bagRef.current = nn.bag;
    setNextPieceType(nn.type);

    const nextPiece = spawnPiece(type);
    if (!isValidPosition(clearedBoard, nextPiece)) {
      setGameState("gameOver");
      setActivePiece(null);
      return;
    }
    setActivePiece(nextPiece);
    setCanHold(true);
  }, [nextPieceType]);

  // Gravity loop
  useEffect(() => {
    if (gameState !== "playing" || !activePiece) return;

    const interval = getGravityInterval(level);
    gravityRef.current = setTimeout(() => {
      const piece = activePieceRef.current;
      if (!piece) return;
      const moved = movePiece(boardRef.current, piece, 0, 1);
      if (moved) {
        setActivePiece(moved);
      } else {
        lockAndClear();
      }
    }, interval);

    return () => {
      if (gravityRef.current) clearTimeout(gravityRef.current);
    };
  }, [gameState, activePiece, level, lockAndClear]);

  const start = useCallback(() => {
    setBoard(createBoard());
    setScore(0);
    setLevel(0);
    setLines(0);
    setHoldPieceType(null);
    setCanHold(true);
    bagRef.current = createBag();
    setGameState("playing");

    // Need a tick for boardRef to update
    setTimeout(() => {
      boardRef.current = createBoard();
      const first = nextFromBag(bagRef.current);
      bagRef.current = first.bag;
      spawnNext(first.type);
    }, 0);
  }, [spawnNext]);

  const moveLeft = useCallback(() => {
    if (gameStateRef.current !== "playing") return;
    const p = activePieceRef.current;
    if (!p) return;
    const moved = movePiece(boardRef.current, p, -1, 0);
    if (moved) setActivePiece(moved);
  }, []);

  const moveRight = useCallback(() => {
    if (gameStateRef.current !== "playing") return;
    const p = activePieceRef.current;
    if (!p) return;
    const moved = movePiece(boardRef.current, p, 1, 0);
    if (moved) setActivePiece(moved);
  }, []);

  const softDrop = useCallback(() => {
    if (gameStateRef.current !== "playing") return;
    const p = activePieceRef.current;
    if (!p) return;
    const moved = movePiece(boardRef.current, p, 0, 1);
    if (moved) {
      setActivePiece(moved);
      setScore((s) => s + 1);
    }
  }, []);

  const hardDropAction = useCallback(() => {
    if (gameStateRef.current !== "playing") return;
    const p = activePieceRef.current;
    if (!p) return;
    const dropped = hardDrop(boardRef.current, p);
    const distance = dropped.y - p.y;
    setScore((s) => s + distance * 2);
    activePieceRef.current = dropped;
    setActivePiece(dropped);
    // Lock immediately
    setTimeout(() => lockAndClear(), 0);
  }, [lockAndClear]);

  const rotate = useCallback(() => {
    if (gameStateRef.current !== "playing") return;
    const p = activePieceRef.current;
    if (!p) return;
    const rotated = rotatePiece(boardRef.current, p, 1);
    if (rotated) setActivePiece(rotated);
  }, []);

  const hold = useCallback(() => {
    if (gameStateRef.current !== "playing") return;
    if (!canHoldRef.current) return;
    const p = activePieceRef.current;
    if (!p) return;

    const prev = holdPieceType;
    setHoldPieceType(p.type);
    setCanHold(false);

    if (prev) {
      const piece = spawnPiece(prev);
      if (isValidPosition(boardRef.current, piece)) {
        setActivePiece(piece);
      }
    } else {
      // No held piece yet, spawn next from queue
      const nn = nextFromBag(bagRef.current);
      bagRef.current = nn.bag;
      setNextPieceType(nn.type);
      const piece = spawnPiece(nextPieceType);
      if (isValidPosition(boardRef.current, piece)) {
        setActivePiece(piece);
      }
    }
  }, [holdPieceType, nextPieceType]);

  return {
    board,
    activePiece,
    nextPiece: nextPieceType,
    holdPiece: holdPieceType,
    canHold,
    score,
    level,
    lines,
    gameState,
    actions: {
      start,
      moveLeft,
      moveRight,
      softDrop,
      hardDropAction,
      rotate,
      hold,
    },
  };
}
