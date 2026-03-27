"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import CollapsiblePanel from "@/components/CollapsiblePanel";
import StatusDot from "@/components/StatusDot";

interface Source {
  editor: string;
  publication: string;
  date: string;
  vertical: string;
  topics: string;
}

interface RawResult {
  href?: string;
  title?: string;
  body: string;
}

interface SkillResult {
  skill_name: string;
  raw_results: RawResult[];
  processed_summary: string;
  error?: string;
}

interface InsightsResult {
  content: string;
  sources: Source[];
  research_skills: SkillResult[];
  audience_timing: string;
  google_trends: string;
}

function SkeletonCard() {
  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 shadow-2xl space-y-4">
      <div className="h-4 w-1/3 bg-surface-container-highest rounded skeleton-pulse" />
      <div className="h-3 w-full bg-surface-container-highest rounded skeleton-pulse" />
      <div className="h-3 w-5/6 bg-surface-container-highest rounded skeleton-pulse" />
      <div className="h-3 w-4/6 bg-surface-container-highest rounded skeleton-pulse" />
      <div className="h-3 w-full bg-surface-container-highest rounded skeleton-pulse" />
      <div className="h-3 w-3/4 bg-surface-container-highest rounded skeleton-pulse" />
    </div>
  );
}

interface ParsedSection {
  title: string;
  content: string;
}

function parseSections(markdown: string): ParsedSection[] {
  const sections: ParsedSection[] = [];
  const parts = markdown.split(/^## /m);

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    const newlineIndex = trimmed.indexOf("\n");
    if (newlineIndex === -1) {
      sections.push({ title: trimmed, content: "" });
    } else {
      sections.push({
        title: trimmed.slice(0, newlineIndex).trim(),
        content: trimmed.slice(newlineIndex + 1).trim(),
      });
    }
  }

  return sections;
}

const markdownComponents = {
  a: ({ href, children, ...props }: React.ComponentPropsWithoutRef<"a">) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-accent-cyan hover:underline break-words"
      {...props}
    >
      {children}
    </a>
  ),
  p: ({ children, ...props }: React.ComponentPropsWithoutRef<"p">) => (
    <p className="mb-4 last:mb-0" {...props}>{children}</p>
  ),
  ul: ({ children, ...props }: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="list-disc list-inside space-y-1 mb-4 last:mb-0" {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }: React.ComponentPropsWithoutRef<"ol">) => (
    <ol className="list-decimal list-inside space-y-1 mb-4 last:mb-0" {...props}>{children}</ol>
  ),
  strong: ({ children, ...props }: React.ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-bold text-on-surface" {...props}>{children}</strong>
  ),
  li: ({ children, ...props }: React.ComponentPropsWithoutRef<"li">) => (
    <li className="text-on-surface-variant" {...props}>{children}</li>
  ),
};

export default function InsightsTool() {
  const [topic, setTopic] = useState("");
  const [advertiser, setAdvertiser] = useState("");
  const [kpi, setKpi] = useState("");
  const [includeTrends, setIncludeTrends] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InsightsResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const KPI_OPTIONS = ["Awareness", "Consideration", "Viewability", "Clicks"];

  const canGenerate = topic.trim() !== "" && advertiser.trim() !== "" && kpi !== "";

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("http://localhost:8000/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          advertiser: advertiser.trim(),
          kpi,
          include_google_trends: includeTrends,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Server error: ${res.status}`);
      }

      const data: InsightsResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />

      <main className="pt-32 pb-20 px-4 md:px-8 min-h-screen">
        <div className="max-w-5xl mx-auto">
          {/* Page header */}
          <div className="mb-12">
            <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tighter mb-4">
              Editorial <span className="text-accent-cyan italic">Insights</span>
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl">
              Generate strategic advertising briefs by combining editorial expertise,
              brand research, audience data, and market trends.
            </p>
          </div>

          {/* Input panel */}
          <GlassCard className="mb-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div>
                <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2 block">
                  Topic
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. gut health, skincare, sustainable fashion"
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface placeholder-slate-500 focus:outline-none focus:border-accent-cyan focus:shadow-[0_0_0_1px_rgba(31,137,223,0.3)] transition-all"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2 block">
                  Advertiser
                </label>
                <input
                  type="text"
                  value={advertiser}
                  onChange={(e) => setAdvertiser(e.target.value)}
                  placeholder="e.g. Yakult, The Ordinary, Patagonia"
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface placeholder-slate-500 focus:outline-none focus:border-accent-cyan focus:shadow-[0_0_0_1px_rgba(31,137,223,0.3)] transition-all"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2 block">
                  KPI
                </label>
                <select
                  value={kpi}
                  onChange={(e) => setKpi(e.target.value)}
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface focus:outline-none focus:border-accent-cyan focus:shadow-[0_0_0_1px_rgba(31,137,223,0.3)] transition-all"
                >
                  <option value="" disabled>Select a KPI</option>
                  {KPI_OPTIONS.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeTrends}
                  onChange={(e) => setIncludeTrends(e.target.checked)}
                  className="w-4 h-4 rounded bg-surface-container-lowest border-outline-variant text-accent-cyan focus:ring-accent-cyan/30 focus:ring-offset-0"
                />
                <span className="text-sm text-on-surface-variant">
                  Include Google Trends data
                </span>
              </label>

              <button
                onClick={handleGenerate}
                disabled={!canGenerate || loading}
                className="refractive-gradient px-8 py-3 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100"
              >
                {loading ? "Generating..." : "Generate Insights"}
              </button>
            </div>
          </GlassCard>

          {/* Error state */}
          {error && (
            <div className="bg-error-container/20 border border-error/30 rounded-xl p-4 mb-8">
              <p className="text-error font-medium">{error}</p>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="space-y-6">
              <SkeletonCard />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            </div>
          )}

          {/* Results */}
          {result && !loading && (() => {
            const sections = parseSections(result.content);
            const keyRecs = sections.find((s) => s.title === "Key Recommendations");
            const detailSections = sections.filter((s) => s.title !== "Key Recommendations");

            return (
            <div className="space-y-6">
              {/* Executive summary banner */}
              {keyRecs && keyRecs.content && (
                <div className="glass-card rounded-2xl p-6 border border-white/10 shadow-2xl border-l-4 border-l-accent-cyan">
                  <div className="mb-4">
                    <StatusDot label="Key Recommendations" />
                  </div>
                  <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
                    <ReactMarkdown components={markdownComponents}>
                      {keyRecs.content}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Detail section cards */}
              {detailSections.map((section, i) => (
                <GlassCard key={i}>
                  <div className="mb-4">
                    <StatusDot label={section.title} />
                  </div>
                  <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
                    <ReactMarkdown components={markdownComponents}>
                      {section.content}
                    </ReactMarkdown>
                  </div>
                </GlassCard>
              ))}

              {/* Sources panel */}
              {result.sources && result.sources.length > 0 && (
                <CollapsiblePanel title="Sources & Attribution" defaultOpen={false}>
                  <ul className="space-y-3">
                    {result.sources.map((source, i) => (
                      <li key={i} className="text-on-surface-variant text-sm">
                        <span className="font-bold text-on-surface">{source.editor}</span>,{" "}
                        {source.publication} ({source.date}) &mdash;{" "}
                        <span className="italic text-accent-cyan">{source.vertical}</span>:{" "}
                        {source.topics}
                      </li>
                    ))}
                  </ul>
                </CollapsiblePanel>
              )}

              {/* Advertiser Research panel */}
              {result.research_skills && result.research_skills.length > 0 && (
                <CollapsiblePanel title="Advertiser Research" defaultOpen={false}>
                  <div className="space-y-6">
                    {result.research_skills.map((skill, i) => (
                      <div
                        key={i}
                        className="bg-surface-container-lowest rounded-xl p-5 border border-white/5"
                      >
                        <h4 className="font-headline font-bold text-lg mb-3">
                          {skill.skill_name}
                        </h4>
                        {skill.error && (
                          <p className="text-error text-sm mb-3">
                            Error: {skill.error}
                          </p>
                        )}
                        <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap mb-4">
                          {skill.processed_summary}
                        </p>

                        {/* Raw snippets */}
                        {skill.raw_results && skill.raw_results.length > 0 && (
                          <ExpandableRawResults results={skill.raw_results} />
                        )}
                      </div>
                    ))}
                  </div>
                </CollapsiblePanel>
              )}

              {/* Audience Data panel */}
              {result.audience_timing && (
                <CollapsiblePanel title="Audience Data" defaultOpen={false}>
                  <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                    {result.audience_timing}
                  </p>
                </CollapsiblePanel>
              )}

              {/* Google Trends panel */}
              {result.google_trends && (
                <CollapsiblePanel title="Google Trends" defaultOpen={false}>
                  <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                    {result.google_trends}
                  </p>
                </CollapsiblePanel>
              )}
            </div>
            );
          })()}

          {/* Empty state */}
          {!result && !loading && !error && (
            <div className="text-center py-20">
              <div className="inline-flex p-6 rounded-2xl bg-surface-container-high mb-6">
                <svg className="w-12 h-12 text-outline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
              </div>
              <p className="text-slate-400 text-lg">
                Enter a topic and advertiser to generate strategic insights.
              </p>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}

function ExpandableRawResults({ results }: { results: RawResult[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-accent-cyan text-xs font-bold tracking-wider uppercase hover:underline"
      >
        {expanded
          ? "Hide raw results"
          : `Show ${results.length} raw snippets`}
      </button>
      {expanded && (
        <ul className="mt-3 space-y-2">
          {results.map((r, j) => (
            <li key={j} className="text-xs text-slate-400">
              {r.href ? (
                <a
                  href={r.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-cyan hover:underline font-medium"
                >
                  {r.title || "Untitled"}
                </a>
              ) : (
                <span className="font-medium text-on-surface-variant">
                  {r.title || "Untitled"}
                </span>
              )}
              : {r.body}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
