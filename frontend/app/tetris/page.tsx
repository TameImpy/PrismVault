"use client";

import { useCallback, useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import GlassCard from "@/components/GlassCard";
import Button from "@/components/Button";
import TetrisBoard from "@/components/tetris/TetrisBoard";
import PiecePreview from "@/components/tetris/PiecePreview";
import Leaderboard from "@/components/tetris/Leaderboard";
import { useTetris } from "@/components/tetris/useTetris";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CONTROLS = [
  { key: "←  →", action: "Move" },
  { key: "↑", action: "Rotate" },
  { key: "↓", action: "Soft drop" },
  { key: "Space", action: "Hard drop" },
  { key: "Shift", action: "Hold" },
];

export default function TetrisPage() {
  const {
    board,
    activePiece,
    nextPiece,
    holdPiece,
    score,
    level,
    lines,
    gameState,
    actions,
  } = useTetris();

  const [playerName, setPlayerName] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [leaderboardKey, setLeaderboardKey] = useState(0);
  const [submittedScore, setSubmittedScore] = useState(false);
  const [finalScore, setFinalScore] = useState(0);
  const [finalLevel, setFinalLevel] = useState(0);
  const [finalLines, setFinalLines] = useState(0);
  const [playerRank, setPlayerRank] = useState<number | null>(null);

  // Load name from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("prism-play-name");
    if (saved) {
      setPlayerName(saved);
      setNameInput(saved);
    }
  }, []);

  // Keyboard controls
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (gameState !== "playing") return;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          actions.moveLeft();
          break;
        case "ArrowRight":
          e.preventDefault();
          actions.moveRight();
          break;
        case "ArrowDown":
          e.preventDefault();
          actions.softDrop();
          break;
        case "ArrowUp":
          e.preventDefault();
          actions.rotate();
          break;
        case " ":
          e.preventDefault();
          actions.hardDropAction();
          break;
        case "Shift":
          e.preventDefault();
          actions.hold();
          break;
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [gameState, actions]);

  // Submit score on game over
  useEffect(() => {
    if (gameState === "gameOver" && !submittedScore) {
      setFinalScore(score);
      setFinalLevel(level);
      setFinalLines(lines);
      setSubmittedScore(true);

      if (playerName) {
        fetch(`${API_BASE}/api/leaderboard`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            player_name: playerName,
            score,
            lines,
            level,
          }),
        })
          .then((res) => res.json())
          .then((data) => {
            setPlayerRank(data.rank);
            setLeaderboardKey((k) => k + 1);
          })
          .catch(() => {});
      }
    }
  }, [gameState, submittedScore, playerName, score, lines, level]);

  const handleStart = useCallback(() => {
    if (!nameInput.trim()) return;
    const name = nameInput.trim();
    setPlayerName(name);
    localStorage.setItem("prism-play-name", name);
    setSubmittedScore(false);
    setPlayerRank(null);
    actions.start();
  }, [nameInput, actions]);

  const handlePlayAgain = useCallback(() => {
    setSubmittedScore(false);
    setPlayerRank(null);
    actions.start();
  }, [actions]);

  const isSplash = gameState === "idle";
  const isPlaying = gameState === "playing";
  const isGameOver = gameState === "gameOver";

  return (
    <div className="min-h-screen bg-surface-container-lowest">
      <Navbar />

      <main className="pt-24 px-4 pb-8 max-w-screen-2xl mx-auto">
        {/* Splash Screen */}
        {isSplash && (
          <div className="flex flex-col items-center justify-center min-h-[70vh] gap-8">
            <div className="text-center space-y-4">
              <h1 className="font-headline text-6xl md:text-8xl font-extrabold tracking-tighter leading-[0.95]">
                Prism{" "}
                <span className="italic bg-clip-text text-transparent refractive-gradient">
                  Play
                </span>
              </h1>
              <p className="text-on-surface-variant text-lg font-body">
                The deep sea Tetris challenge
              </p>
            </div>

            <GlassCard className="w-full max-w-sm">
              <label className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant font-label block mb-2">
                Player Name
              </label>
              <input
                type="text"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleStart()}
                maxLength={15}
                placeholder="Enter your name..."
                className="w-full bg-surface-container-lowest text-on-surface px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-accent-cyan/50 transition-all font-body placeholder:text-on-surface-variant/40"
              />
              <Button
                onClick={handleStart}
                disabled={!nameInput.trim()}
                className="w-full mt-4 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Start Game
              </Button>
            </GlassCard>

            <div className="w-full max-w-sm">
              <Leaderboard playerName={playerName} refreshKey={leaderboardKey} />
            </div>
          </div>
        )}

        {/* Game Screen */}
        {(isPlaying || isGameOver) && (
          <div className="flex flex-col xl:flex-row items-start justify-center gap-6">
            {/* Left Panel */}
            <div className="w-48 space-y-6 hidden xl:block">
              <GlassCard>
                <PiecePreview type={holdPiece} label="Hold" />
              </GlassCard>

              <GlassCard>
                <PiecePreview type={nextPiece} label="Next" />
              </GlassCard>

              <GlassCard>
                <div className="space-y-4">
                  <div>
                    <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant font-label">
                      Score
                    </p>
                    <p className="text-2xl font-bold font-mono text-on-surface tracking-tight">
                      {score.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant font-label">
                      Level
                    </p>
                    <p className="text-2xl font-bold font-mono text-accent-cyan">
                      {level}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant font-label">
                      Lines
                    </p>
                    <p className="text-2xl font-bold font-mono text-on-surface">
                      {lines}
                    </p>
                  </div>
                </div>
              </GlassCard>

              <GlassCard>
                <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant font-label mb-3">
                  Controls
                </p>
                <div className="space-y-2">
                  {CONTROLS.map(({ key, action }) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="bg-surface-container-lowest px-2 py-0.5 rounded font-mono text-accent-cyan text-[10px]">
                        {key}
                      </span>
                      <span className="text-on-surface-variant">{action}</span>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </div>

            {/* Center: Game Board */}
            <div className="relative">
              <TetrisBoard board={board} activePiece={activePiece} />

              {/* Mobile info bar (below board on small screens) */}
              <div className="flex xl:hidden items-center justify-between mt-4 gap-4">
                <div className="text-center">
                  <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant">Score</p>
                  <p className="font-bold font-mono text-on-surface">{score.toLocaleString()}</p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant">Level</p>
                  <p className="font-bold font-mono text-accent-cyan">{level}</p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant">Lines</p>
                  <p className="font-bold font-mono text-on-surface">{lines}</p>
                </div>
              </div>

              {/* Game Over Modal */}
              {isGameOver && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm rounded-xl">
                  <GlassCard className="text-center space-y-4 max-w-[240px]">
                    <h2 className="font-headline text-2xl font-bold tracking-tight text-on-surface">
                      Game Over
                    </h2>
                    <div className="space-y-2">
                      <p className="text-3xl font-bold font-mono text-accent-cyan">
                        {finalScore.toLocaleString()}
                      </p>
                      <div className="flex justify-center gap-4 text-sm text-on-surface-variant">
                        <span>Level {finalLevel}</span>
                        <span>{finalLines} lines</span>
                      </div>
                      {playerRank && (
                        <p className="text-sm">
                          Rank:{" "}
                          <span className="font-bold text-accent-cyan">#{playerRank}</span>
                        </p>
                      )}
                    </div>
                    <Button onClick={handlePlayAgain} className="w-full">
                      Play Again
                    </Button>
                  </GlassCard>
                </div>
              )}
            </div>

            {/* Right Panel: Leaderboard */}
            <div className="w-72 hidden xl:block">
              <Leaderboard playerName={playerName} refreshKey={leaderboardKey} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
