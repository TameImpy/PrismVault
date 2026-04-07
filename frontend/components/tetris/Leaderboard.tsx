"use client";

import { useEffect, useState, useCallback } from "react";
import GlassCard from "../GlassCard";

interface LeaderboardEntry {
  rank: number;
  player_name: string;
  score: number;
  lines: number;
  level: number;
}

interface LeaderboardData {
  top_10: LeaderboardEntry[];
  player_rank: number | null;
  total_players: number;
}

interface LeaderboardProps {
  playerName: string;
  refreshKey: number; // increment to trigger refresh
}

export default function Leaderboard({ playerName, refreshKey }: LeaderboardProps) {
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchLeaderboard = useCallback(async () => {
    try {
      setLoading(true);
      const params = playerName ? `?player_name=${encodeURIComponent(playerName)}` : "";
      const res = await fetch(`/api/leaderboard${params}`);
      if (res.ok) {
        setData(await res.json());
      }
    } catch {
      // Silently fail — leaderboard is non-critical
    } finally {
      setLoading(false);
    }
  }, [playerName]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard, refreshKey]);

  return (
    <GlassCard className="h-full">
      <h2 className="font-headline font-bold text-lg tracking-tight text-on-surface mb-4 flex items-center gap-2">
        <span className="w-1.5 h-5 bg-accent-cyan rounded-full" />
        Leaderboard
      </h2>

      {loading && !data && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 bg-surface-container-lowest rounded-lg skeleton-pulse" />
          ))}
        </div>
      )}

      {data && (
        <>
          {data.top_10.length === 0 ? (
            <p className="text-on-surface-variant text-sm">No scores yet. Be the first!</p>
          ) : (
            <div className="space-y-1">
              {data.top_10.map((entry, i) => (
                <div
                  key={i}
                  className={`flex items-center justify-between py-2 px-3 rounded-lg text-sm ${
                    entry.player_name === playerName
                      ? "bg-accent-cyan/10 text-accent-cyan"
                      : "text-on-surface-variant hover:bg-surface-container-lowest/50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 text-right font-bold text-[10px] tracking-widest">
                      {entry.rank <= 3 ? ["🥇", "🥈", "🥉"][entry.rank - 1] : `#${entry.rank}`}
                    </span>
                    <span className="font-semibold truncate max-w-[100px]">
                      {entry.player_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-xs text-on-surface-variant">
                      L{entry.level}
                    </span>
                    <span className="font-bold font-mono w-16 text-right">
                      {entry.score.toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {data.player_rank && data.player_rank > 10 && (
            <div className="mt-4 pt-3 border-t border-outline-variant/20">
              <div className="flex items-center justify-between text-sm text-accent-cyan px-3">
                <div className="flex items-center gap-3">
                  <span className="w-6 text-right font-bold text-[10px]">#{data.player_rank}</span>
                  <span className="font-semibold">{playerName}</span>
                </div>
                <span className="text-[10px] tracking-widest uppercase text-on-surface-variant">
                  Your rank
                </span>
              </div>
            </div>
          )}

          <p className="text-[10px] tracking-widest uppercase text-on-surface-variant mt-4 text-center">
            {data.total_players} player{data.total_players !== 1 ? "s" : ""} total
          </p>
        </>
      )}
    </GlassCard>
  );
}
