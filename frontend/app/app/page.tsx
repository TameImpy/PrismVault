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
  format_recommendations: string;
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

const GLANCE_ICONS: Record<string, React.ReactNode> = {
  "Core Products": (
    <svg className="w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
    </svg>
  ),
  "Latest News": (
    <svg className="w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 002.25 2.25h13.5M6 7.5h3v3H6v-3z" />
    </svg>
  ),
  "Messaging": (
    <svg className="w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46" />
    </svg>
  ),
  "Tone": (
    <svg className="w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" />
    </svg>
  ),
  "Editor Voice": (
    <svg className="w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
    </svg>
  ),
  "Top Format": (
    <svg className="w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  ),
};

interface GlanceCard {
  label: string;
  content: string;
}

function parseGlanceCards(sectionContent: string): GlanceCard[] {
  return sectionContent
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.includes(":"))
    .map((line) => {
      const colonIndex = line.indexOf(":");
      return {
        label: line.slice(0, colonIndex).trim(),
        content: line.slice(colonIndex + 1).trim(),
      };
    })
    .filter((card) => card.label && card.content);
}

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
            const atAGlance = sections.find((s) => s.title === "At a Glance");
            const keyRecs = sections.find((s) => s.title === "Key Recommendations");
            const detailSections = sections.filter(
              (s) => s.title !== "Key Recommendations" && s.title !== "At a Glance"
            );
            const glanceCards = atAGlance ? parseGlanceCards(atAGlance.content) : [];

            return (
            <div className="space-y-6">
              {/* At a Glance dashboard */}
              {glanceCards.length > 0 && (
                <GlassCard>
                  <div className="mb-4">
                    <StatusDot label="At a Glance" />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {glanceCards.map((card, i) => (
                      <div
                        key={i}
                        className="bg-surface-container-lowest rounded-xl p-4 border border-white/5 flex items-start gap-3"
                      >
                        <div className="shrink-0 mt-0.5">
                          {GLANCE_ICONS[card.label] || GLANCE_ICONS["Core Products"]}
                        </div>
                        <div>
                          <p className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-1">
                            {card.label}
                          </p>
                          <p className="text-on-surface text-sm leading-relaxed">
                            {card.content}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}

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

              {/* Format Recommendations panel */}
              {result.format_recommendations && (
                <CollapsiblePanel title="Format Recommendations" defaultOpen={false}>
                  <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                    {result.format_recommendations}
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
