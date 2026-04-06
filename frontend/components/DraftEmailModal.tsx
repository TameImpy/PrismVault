"use client";

import { useState, useEffect } from "react";

interface DraftEmailModalProps {
  open: boolean;
  onClose: () => void;
  briefContent: string;
  topic: string;
  advertiser: string;
  kpi: string;
  sampleCount: number;
  onSampleCountChange?: (count: number) => void;
  track?: (event: string, properties?: Record<string, unknown>) => void;
}

const API_BASE = "http://localhost:8000";

export default function DraftEmailModal({
  open,
  onClose,
  briefContent,
  topic,
  advertiser,
  kpi,
  sampleCount,
  onSampleCountChange,
  track,
}: DraftEmailModalProps) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [onboardingText, setOnboardingText] = useState("");
  const [savingOnboard, setSavingOnboard] = useState(false);

  const needsOnboarding = sampleCount === 0;

  async function generateDraft(isRegenerate = false) {
    setLoading(true);
    setError("");
    setCopied(false);
    const startTime = Date.now();
    try {
      const res = await fetch(`${API_BASE}/api/draft-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ content: briefContent, topic, advertiser, kpi }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Failed to generate draft");
      }
      const data = await res.json();
      setSubject(data.subject);
      setBody(data.body);
      const eventName = isRegenerate ? "Draft Email Regenerated" : "Draft Email Generated";
      track?.(eventName, {
        topic,
        advertiser,
        kpi,
        sample_count: sampleCount,
        duration_ms: Date.now() - startTime,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate draft");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open && !needsOnboarding && !subject && !body && !loading) {
      generateDraft();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function handleSaveAndDraft() {
    if (!onboardingText.trim()) return;
    setSavingOnboard(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/email-samples`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ content: onboardingText.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Failed to save sample");
      }
      onSampleCountChange?.(sampleCount + 1);
      track?.("Writing Sample Added");
      setOnboardingText("");
      await generateDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save sample");
    } finally {
      setSavingOnboard(false);
    }
  }

  function handleCopy() {
    const text = subject ? `Subject: ${subject}\n\n${body}` : body;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      track?.("Draft Email Copied");
    });
  }

  function handleRegenerate() {
    setSubject("");
    setBody("");
    generateDraft(true);
  }

  function handleClose() {
    setSubject("");
    setBody("");
    setError("");
    setCopied(false);
    setOnboardingText("");
    onClose();
  }

  if (!open) return null;

  const showOnboarding = needsOnboarding && !subject && !body && !loading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />
      <div className="relative w-full max-w-2xl mx-4 glass-card rounded-2xl border border-white/10 shadow-2xl p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-headline text-xl font-bold text-white">
            {showOnboarding ? "Set up your writing style" : "Draft Email"}
          </h2>
          <button
            onClick={handleClose}
            className="text-on-surface-variant hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Onboarding mode */}
        {showOnboarding && (
          <div>
            <p className="text-on-surface-variant text-sm mb-4">
              To draft emails in your voice, paste a sample email you&apos;ve sent to a client.
              This helps the AI match your writing style. You can add more samples later.
            </p>
            <textarea
              value={onboardingText}
              onChange={(e) => setOnboardingText(e.target.value)}
              placeholder="Hi Sarah, I wanted to reach out about an exciting opportunity we've identified..."
              rows={8}
              className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-all resize-y text-sm"
            />
            <div className="flex justify-end mt-4">
              <button
                onClick={handleSaveAndDraft}
                disabled={!onboardingText.trim() || savingOnboard}
                className="refractive-gradient px-6 py-2.5 rounded-xl font-bold text-white text-sm shadow-lg active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {savingOnboard ? "Saving & drafting..." : "Save & Draft"}
              </button>
            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-accent-cyan/30 border-t-accent-cyan rounded-full animate-spin mb-4" />
            <p className="text-on-surface-variant text-sm">Drafting your email...</p>
          </div>
        )}

        {/* Draft result */}
        {!loading && (subject || body) && (
          <>
            {subject && (
              <div className="mb-4">
                <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-1 block">
                  Subject
                </label>
                <div className="bg-surface-container-lowest rounded-xl px-4 py-3 border border-white/5 text-on-surface text-sm font-medium">
                  {subject}
                </div>
              </div>
            )}

            <div className="mb-6">
              <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-1 block">
                Body
              </label>
              <div className="bg-surface-container-lowest rounded-xl px-4 py-4 border border-white/5 text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                {body}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleCopy}
                className="refractive-gradient px-6 py-2.5 rounded-xl font-bold text-white text-sm shadow-lg active:scale-95 transition-all"
              >
                {copied ? "Copied!" : "Copy to clipboard"}
              </button>
              <button
                onClick={handleRegenerate}
                className="px-6 py-2.5 rounded-xl font-bold text-on-surface-variant hover:text-white border border-white/10 hover:border-white/20 text-sm transition-all active:scale-95"
              >
                Regenerate
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
