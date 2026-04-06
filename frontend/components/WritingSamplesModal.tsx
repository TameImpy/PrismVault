"use client";

import { useState, useEffect, useCallback } from "react";

interface Sample {
  id: number;
  content: string;
  created_at: string;
}

interface WritingSamplesModalProps {
  open: boolean;
  onClose: () => void;
  onSampleCountChange?: (count: number) => void;
  track?: (event: string, properties?: Record<string, unknown>) => void;
}

const API_BASE = "http://localhost:8000";

export default function WritingSamplesModal({
  open,
  onClose,
  onSampleCountChange,
  track,
}: WritingSamplesModalProps) {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [newContent, setNewContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchSamples = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/email-samples`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setSamples(data);
        onSampleCountChange?.(data.length);
      }
    } catch {
      // silently fail on fetch
    }
  }, [onSampleCountChange]);

  useEffect(() => {
    if (open) {
      fetchSamples();
    }
  }, [open, fetchSamples]);

  async function handleAdd() {
    if (!newContent.trim()) return;
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/email-samples`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ content: newContent.trim() }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to add sample");
      }
      setNewContent("");
      track?.("Writing Sample Added");
      await fetchSamples();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add sample");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await fetch(`${API_BASE}/api/email-samples/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      track?.("Writing Sample Deleted");
      await fetchSamples();
    } catch {
      // silently fail
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 glass-card rounded-2xl border border-white/10 shadow-2xl p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-headline text-xl font-bold text-white">
            Writing Style Samples
          </h2>
          <span className="text-sm text-on-surface-variant">
            {samples.length} of 5
          </span>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Existing samples */}
        {samples.length > 0 && (
          <div className="space-y-3 mb-6">
            {samples.map((sample) => (
              <div
                key={sample.id}
                className="bg-surface-container-lowest rounded-xl p-4 border border-white/5 flex items-start gap-3"
              >
                <p className="text-on-surface-variant text-sm flex-1 line-clamp-3">
                  {sample.content}
                </p>
                <button
                  onClick={() => handleDelete(sample.id)}
                  className="shrink-0 text-red-400 hover:text-red-300 transition-colors p-1"
                  title="Delete sample"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add new sample */}
        {samples.length < 5 && (
          <div>
            <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2 block">
              Paste a past email you&apos;ve sent
            </label>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Hi Sarah, I wanted to reach out about an exciting opportunity we've identified..."
              rows={5}
              className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-all resize-y text-sm"
            />
            <div className="flex justify-end mt-3">
              <button
                onClick={handleAdd}
                disabled={!newContent.trim() || loading}
                className="refractive-gradient px-6 py-2.5 rounded-xl font-bold text-white text-sm shadow-lg active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? "Saving..." : "Save Sample"}
              </button>
            </div>
          </div>
        )}

        <div className="flex justify-end mt-6 pt-4 border-t border-white/5">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-xl font-bold text-on-surface-variant hover:text-white transition-colors text-sm"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
