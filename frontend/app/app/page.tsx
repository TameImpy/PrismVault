"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import CollapsiblePanel from "@/components/CollapsiblePanel";
import WritingSamplesModal from "@/components/WritingSamplesModal";
import DraftEmailModal from "@/components/DraftEmailModal";
import AudienceSegmentsPanel from "@/components/AudienceSegmentsPanel";
import { useAnalytics } from "@/components/AnalyticsProvider";
import { useAuth } from "@/contexts/AuthContext";
import { AudienceSegmentsPayload } from "@/lib/audienceSegments";

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
  audience_segments: AudienceSegmentsPayload;
  google_trends: string;
  format_recommendations: string;
  campaign_history: string;
  client_brief_summary: string;
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
    <p className="mb-4 last:mb-0" {...props}>
      {children}
    </p>
  ),
  ul: ({ children, ...props }: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="list-disc list-inside space-y-1 mb-4 last:mb-0" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }: React.ComponentPropsWithoutRef<"ol">) => (
    <ol
      className="list-decimal list-inside space-y-1 mb-4 last:mb-0"
      {...props}
    >
      {children}
    </ol>
  ),
  strong: ({
    children,
    ...props
  }: React.ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-bold text-on-surface" {...props}>
      {children}
    </strong>
  ),
  li: ({ children, ...props }: React.ComponentPropsWithoutRef<"li">) => (
    <li className="text-on-surface-variant" {...props}>
      {children}
    </li>
  ),
};

const GLANCE_ICONS: Record<string, React.ReactNode> = {
  "Core Products": (
    <svg
      className="w-6 h-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
      />
    </svg>
  ),
  "Latest News": (
    <svg
      className="w-6 h-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 002.25 2.25h13.5M6 7.5h3v3H6v-3z"
      />
    </svg>
  ),
  Messaging: (
    <svg
      className="w-6 h-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46"
      />
    </svg>
  ),
  Tone: (
    <svg
      className="w-6 h-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42"
      />
    </svg>
  ),
  "Editor Voice": (
    <svg
      className="w-6 h-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
      />
    </svg>
  ),
  "Top Format": (
    <svg
      className="w-6 h-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
      />
    </svg>
  ),
};

const SECTION_ICONS: Record<string, React.ReactNode> = {
  "Key Recommendations": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"
      />
    </svg>
  ),
  "Advertiser Overview": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z"
      />
    </svg>
  ),
  "Editorial Insights": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
      />
    </svg>
  ),
  "Strategic Alignment": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.491 48.491 0 01-4.163-.3c.186 1.613.95 3.033 2.07 4.067v0a.64.64 0 010 .918 48.523 48.523 0 01-1.834 1.607c1.175.906 2.627 1.403 4.159 1.403s2.984-.497 4.159-1.403a48.57 48.57 0 01-1.834-1.607.64.64 0 010-.918v0c1.12-1.034 1.884-2.454 2.07-4.067a48.49 48.49 0 01-4.163.3.64.64 0 01-.657-.643v0z"
      />
    </svg>
  ),
  "Audience Segments & Reach": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
      />
    </svg>
  ),
  "Recommended Products": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
      />
    </svg>
  ),
  "Messaging & Tone Recommendations": (
    <svg
      className="w-7 h-7"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46"
      />
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
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login?redirect=/app");
    }
  }, [authLoading, user, router]);

  const [topic, setTopic] = useState("");
  const [advertiser, setAdvertiser] = useState("");
  const [kpi, setKpi] = useState("");
  const [clientBrief, setClientBrief] = useState("");
  const [includeTrends, setIncludeTrends] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InsightsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [samplesModalOpen, setSamplesModalOpen] = useState(false);
  const [draftModalOpen, setDraftModalOpen] = useState(false);
  const [sampleCount, setSampleCount] = useState(0);
  const [deckLoading, setDeckLoading] = useState(false);
  const { track } = useAnalytics();

  // Brief library state
  type TabName = "new" | "mine" | "team";
  const [activeTab, setActiveTab] = useState<TabName>("new");
  const [briefs, setBriefs] = useState<any[]>([]);
  const [briefsLoading, setBriefsLoading] = useState(false);
  const [briefSearch, setBriefSearch] = useState("");
  const [viewingBrief, setViewingBrief] = useState<any | null>(null);
  const [viewingBriefLoading, setViewingBriefLoading] = useState(false);

  const fetchBriefs = useCallback(async (scope: string) => {
    setBriefsLoading(true);
    try {
      const res = await fetch("/api/briefs?scope=" + scope, {
        credentials: "include",
      });
      if (res.ok) setBriefs(await res.json());
    } catch {}
    setBriefsLoading(false);
  }, []);

  useEffect(() => {
    if (activeTab === "mine") fetchBriefs("mine");
    else if (activeTab === "team") fetchBriefs("team");
  }, [activeTab, fetchBriefs]);

  async function openBrief(id: number) {
    setViewingBriefLoading(true);
    try {
      const res = await fetch("/api/briefs/" + id, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        data._parsed_result = JSON.parse(data.result_json);
        setViewingBrief(data);
      }
    } catch {}
    setViewingBriefLoading(false);
  }

  async function handleDeleteBrief(id: number) {
    const res = await fetch("/api/briefs/" + id, {
      method: "DELETE",
      credentials: "include",
    });
    if (res.ok) {
      setBriefs((prev) => prev.filter((b) => b.id !== id));
      if (viewingBrief?.id === id) setViewingBrief(null);
    }
  }

  function handleRerun(brief: any) {
    setTopic(brief.topic);
    setAdvertiser(brief.advertiser);
    setKpi(brief.kpi);
    setClientBrief(brief.client_brief || "");
    setViewingBrief(null);
    setActiveTab("new");
  }

  const handleSampleCountChange = useCallback((count: number) => {
    setSampleCount(count);
  }, []);

  // Fetch sample count on mount
  useEffect(() => {
    fetch("/api/email-samples", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setSampleCount(Array.isArray(data) ? data.length : 0))
      .catch(() => {});
  }, []);

  const KPI_OPTIONS = ["Awareness", "Consideration", "Viewability", "Clicks"];

  if (authLoading || !user) return null;

  const canGenerate =
    topic.trim() !== "" && advertiser.trim() !== "" && kpi !== "";

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    setResult(null);

    const eventProps = {
      topic: topic.trim(),
      advertiser: advertiser.trim(),
      kpi,
      include_google_trends: includeTrends,
      has_client_brief: clientBrief.trim() !== "",
    };

    track("Insights Requested", eventProps);
    const startTime = Date.now();

    try {
      const res = await fetch("/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          topic: topic.trim(),
          advertiser: advertiser.trim(),
          kpi,
          include_google_trends: includeTrends,
          client_brief: clientBrief.trim(),
        }),
      });

      if (!res.ok) {
        if (res.status === 401) {
          router.push("/login?redirect=/app");
          return;
        }
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Server error: ${res.status}`);
      }

      const data: InsightsResult = await res.json();
      setResult(data);
      track("Insights Generated", {
        ...eventProps,
        duration_ms: Date.now() - startTime,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
      track("Insights Failed", {
        ...eventProps,
        error_message: message,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />

      <main className="pt-32 pb-20 px-4 md:px-8 min-h-screen relative">
        {/* Decorative floating cube */}
        <div className="absolute top-24 right-8 animate-float pointer-events-none opacity-20 hidden lg:block">
          <img src="/cube.png" alt="" className="w-24 h-24" />
        </div>

        <div className="max-w-5xl mx-auto">
          {/* Page header */}
          <div className="mb-8">
            <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tighter mb-4">
              Prism <span className="text-accent-cyan italic">Plan</span>
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl">
              Generate strategic advertising briefs by combining editorial
              expertise, brand research, audience data, and market trends.
            </p>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-8 bg-surface-container rounded-xl p-1 w-fit">
            {(
              [
                ["new", "New Brief"],
                ["mine", "My Briefs"],
                ["team", "Team Library"],
              ] as [TabName, string][]
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => {
                  setActiveTab(key);
                  setViewingBrief(null);
                }}
                className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === key
                    ? "bg-accent-cyan/15 text-accent-cyan"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Brief list view (My Briefs / Team Library) */}
          {activeTab !== "new" && !viewingBrief && (
            <div>
              <div className="mb-6">
                <input
                  type="text"
                  value={briefSearch}
                  onChange={(e) => setBriefSearch(e.target.value)}
                  placeholder="Search by advertiser, topic, or author..."
                  className="w-full md:w-96 bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface placeholder-slate-500 focus:outline-none focus:border-accent-cyan focus:shadow-[0_0_0_1px_rgba(31,137,223,0.3)] transition-all text-sm"
                />
              </div>

              {briefsLoading ? (
                <div className="space-y-4">
                  <SkeletonCard />
                  <SkeletonCard />
                </div>
              ) : briefs.length === 0 ? (
                <div className="text-center py-20">
                  <p className="text-slate-400 text-lg">
                    {activeTab === "mine"
                      ? "You haven't generated any briefs yet."
                      : "No briefs have been generated yet."}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {briefs
                    .filter((b) => {
                      if (!briefSearch.trim()) return true;
                      const q = briefSearch.toLowerCase();
                      return (
                        b.advertiser?.toLowerCase().includes(q) ||
                        b.topic?.toLowerCase().includes(q) ||
                        (b.author_name &&
                          b.author_name.toLowerCase().includes(q))
                      );
                    })
                    .map((brief) => (
                      <button
                        key={brief.id}
                        onClick={() => openBrief(brief.id)}
                        className="w-full text-left glass-card rounded-2xl p-5 border border-white/10 shadow-2xl hover:border-accent-cyan/30 hover:shadow-[0_0_20px_rgba(31,137,223,0.1)] transition-all duration-300 flex items-center justify-between group"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-1">
                            <span className="font-headline font-bold text-white text-lg truncate">
                              {brief.advertiser}
                            </span>
                            <span className="px-2 py-0.5 rounded-md bg-accent-cyan/10 text-accent-cyan text-xs font-semibold shrink-0">
                              {brief.kpi}
                            </span>
                          </div>
                          <p className="text-slate-400 text-sm truncate">
                            {brief.topic}
                          </p>
                          <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                            {brief.author_name && (
                              <span>{brief.author_name}</span>
                            )}
                            <span>
                              {new Date(brief.created_at).toLocaleDateString(
                                "en-GB",
                                {
                                  day: "numeric",
                                  month: "short",
                                  year: "numeric",
                                },
                              )}
                            </span>
                          </div>
                        </div>
                        {brief.user_id === user?.id && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteBrief(brief.id);
                            }}
                            className="ml-4 p-2 text-slate-500 hover:text-error transition-colors opacity-0 group-hover:opacity-100"
                            title="Delete brief"
                          >
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                              />
                            </svg>
                          </button>
                        )}
                      </button>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* Brief detail view (from saved brief) */}
          {viewingBrief &&
            activeTab !== "new" &&
            (() => {
              const briefResult: InsightsResult = viewingBrief._parsed_result;
              const sections = parseSections(briefResult.content);
              const atAGlance = sections.find((s) => s.title === "At a Glance");
              const keyRecs = sections.find(
                (s) => s.title === "Key Recommendations",
              );
              const detailSections = sections.filter(
                (s) =>
                  s.title !== "Key Recommendations" &&
                  s.title !== "At a Glance",
              );
              const glanceCards = atAGlance
                ? parseGlanceCards(atAGlance.content)
                : [];

              // Temporarily set result for deck/email actions
              const savedResult = briefResult;

              return (
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <button
                      onClick={() => setViewingBrief(null)}
                      className="text-accent-cyan text-sm font-semibold hover:underline flex items-center gap-1"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 19l-7-7 7-7"
                        />
                      </svg>
                      Back to list
                    </button>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-500">
                        {viewingBrief.author_name} &middot;{" "}
                        {new Date(viewingBrief.created_at).toLocaleDateString(
                          "en-GB",
                          { day: "numeric", month: "short", year: "numeric" },
                        )}
                      </span>
                      <button
                        onClick={() => handleRerun(viewingBrief)}
                        className="px-4 py-2 rounded-lg text-sm font-semibold text-accent-cyan bg-accent-cyan/10 hover:bg-accent-cyan/20 transition-all"
                      >
                        Re-run
                      </button>
                    </div>
                  </div>

                  <div className="mb-4">
                    <h2 className="font-headline text-2xl font-bold text-white">
                      {viewingBrief.advertiser}
                    </h2>
                    <p className="text-slate-400">
                      {viewingBrief.topic} &middot; {viewingBrief.kpi}
                    </p>
                  </div>

                  <div className="space-y-6">
                    {glanceCards.length > 0 && (
                      <div className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5">
                        <h2 className="font-headline text-2xl font-bold mb-6">
                          At a Glance
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {glanceCards.map((card, i) => (
                            <div
                              key={i}
                              className="bg-surface-container rounded-xl p-4 border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 flex items-start gap-3"
                            >
                              <div className="shrink-0 inline-flex p-2.5 rounded-xl bg-accent-cyan/10 text-accent-cyan">
                                {GLANCE_ICONS[card.label] ||
                                  GLANCE_ICONS["Core Products"]}
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
                      </div>
                    )}

                    {keyRecs && keyRecs.content && (
                      <div className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5 border-l-4 border-l-accent-cyan">
                        <div className="mb-6 inline-flex p-3 rounded-xl bg-accent-cyan/10 text-accent-cyan">
                          {SECTION_ICONS["Key Recommendations"]}
                        </div>
                        <h2 className="font-headline text-2xl font-bold mb-4">
                          Key Recommendations
                        </h2>
                        <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
                          <ReactMarkdown components={markdownComponents}>
                            {keyRecs.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}

                    {detailSections.map((section, i) => (
                      <div
                        key={i}
                        className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5 hover:border-accent-cyan/20 transition-all duration-500"
                      >
                        {SECTION_ICONS[section.title] && (
                          <div className="mb-6 inline-flex p-3 rounded-xl bg-accent-cyan/10 text-accent-cyan">
                            {SECTION_ICONS[section.title]}
                          </div>
                        )}
                        <h2 className="font-headline text-2xl font-bold mb-4">
                          {section.title}
                        </h2>
                        <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
                          <ReactMarkdown components={markdownComponents}>
                            {section.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ))}

                    {savedResult.sources && savedResult.sources.length > 0 && (
                      <CollapsiblePanel
                        title="Sources & Attribution"
                        defaultOpen={false}
                      >
                        <ul className="space-y-3">
                          {savedResult.sources.map((source, i) => (
                            <li
                              key={i}
                              className="text-on-surface-variant text-sm"
                            >
                              <span className="font-bold text-on-surface">
                                {source.editor}
                              </span>
                              , {source.publication} ({source.date}) &mdash;{" "}
                              <span className="italic text-accent-cyan">
                                {source.vertical}
                              </span>
                              : {source.topics}
                            </li>
                          ))}
                        </ul>
                      </CollapsiblePanel>
                    )}

                    {savedResult.research_skills &&
                      savedResult.research_skills.length > 0 && (
                        <CollapsiblePanel
                          title="Advertiser Research"
                          defaultOpen={false}
                        >
                          <div className="space-y-6">
                            {savedResult.research_skills.map((skill, i) => (
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
                                {skill.raw_results &&
                                  skill.raw_results.length > 0 && (
                                    <ExpandableRawResults
                                      results={skill.raw_results}
                                    />
                                  )}
                              </div>
                            ))}
                          </div>
                        </CollapsiblePanel>
                      )}

                    <AudienceSegmentsPanel
                      data={savedResult.audience_segments}
                    />

                    {savedResult.google_trends && (
                      <CollapsiblePanel
                        title="Google Trends"
                        defaultOpen={false}
                      >
                        <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                          {savedResult.google_trends}
                        </p>
                      </CollapsiblePanel>
                    )}
                  </div>
                </div>
              );
            })()}

          {/* Input panel — only show on New Brief tab */}
          {activeTab === "new" && (
            <>
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
                      <option value="" disabled>
                        Select a KPI
                      </option>
                      {KPI_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="mb-6">
                  <label className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase mb-2 block">
                    Client Brief (optional)
                  </label>
                  <textarea
                    value={clientBrief}
                    onChange={(e) => setClientBrief(e.target.value)}
                    placeholder="e.g. Client wants to drive awareness among 25-34 women, launching a new skincare range in September, budget is mid-tier, open to digital and social formats"
                    rows={3}
                    className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 text-on-surface placeholder-slate-500 focus:outline-none focus:border-accent-cyan focus:shadow-[0_0_0_1px_rgba(31,137,223,0.3)] transition-all resize-y"
                  />
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
              {result &&
                !loading &&
                (() => {
                  const sections = parseSections(result.content);
                  const atAGlance = sections.find(
                    (s) => s.title === "At a Glance",
                  );
                  const keyRecs = sections.find(
                    (s) => s.title === "Key Recommendations",
                  );
                  const detailSections = sections.filter(
                    (s) =>
                      s.title !== "Key Recommendations" &&
                      s.title !== "At a Glance",
                  );
                  const glanceCards = atAGlance
                    ? parseGlanceCards(atAGlance.content)
                    : [];

                  return (
                    <div className="space-y-6">
                      {/* At a Glance dashboard */}
                      {glanceCards.length > 0 && (
                        <div className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5">
                          <h2 className="font-headline text-2xl font-bold mb-6">
                            At a Glance
                          </h2>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {glanceCards.map((card, i) => (
                              <div
                                key={i}
                                className="bg-surface-container rounded-xl p-4 border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 flex items-start gap-3"
                              >
                                <div className="shrink-0 inline-flex p-2.5 rounded-xl bg-accent-cyan/10 text-accent-cyan">
                                  {GLANCE_ICONS[card.label] ||
                                    GLANCE_ICONS["Core Products"]}
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
                        </div>
                      )}

                      {/* Executive summary banner */}
                      {keyRecs && keyRecs.content && (
                        <div className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5 border-l-4 border-l-accent-cyan">
                          <div className="mb-6 inline-flex p-3 rounded-xl bg-accent-cyan/10 text-accent-cyan">
                            {SECTION_ICONS["Key Recommendations"]}
                          </div>
                          <h2 className="font-headline text-2xl font-bold mb-4">
                            Key Recommendations
                          </h2>
                          <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
                            <ReactMarkdown components={markdownComponents}>
                              {keyRecs.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )}

                      {/* Detail section cards */}
                      {detailSections.map((section, i) => (
                        <div
                          key={i}
                          className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5 hover:border-accent-cyan/20 transition-all duration-500"
                        >
                          {SECTION_ICONS[section.title] && (
                            <div className="mb-6 inline-flex p-3 rounded-xl bg-accent-cyan/10 text-accent-cyan">
                              {SECTION_ICONS[section.title]}
                            </div>
                          )}
                          <h2 className="font-headline text-2xl font-bold mb-4">
                            {section.title}
                          </h2>
                          <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
                            <ReactMarkdown components={markdownComponents}>
                              {section.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      ))}

                      {/* Sources panel */}
                      {result.sources && result.sources.length > 0 && (
                        <CollapsiblePanel
                          title="Sources & Attribution"
                          defaultOpen={false}
                        >
                          <ul className="space-y-3">
                            {result.sources.map((source, i) => (
                              <li
                                key={i}
                                className="text-on-surface-variant text-sm"
                              >
                                <span className="font-bold text-on-surface">
                                  {source.editor}
                                </span>
                                , {source.publication} ({source.date}) &mdash;{" "}
                                <span className="italic text-accent-cyan">
                                  {source.vertical}
                                </span>
                                : {source.topics}
                              </li>
                            ))}
                          </ul>
                        </CollapsiblePanel>
                      )}

                      {/* Advertiser Research panel */}
                      {result.research_skills &&
                        result.research_skills.length > 0 && (
                          <CollapsiblePanel
                            title="Advertiser Research"
                            defaultOpen={false}
                          >
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
                                  {skill.raw_results &&
                                    skill.raw_results.length > 0 && (
                                      <ExpandableRawResults
                                        results={skill.raw_results}
                                      />
                                    )}
                                </div>
                              ))}
                            </div>
                          </CollapsiblePanel>
                        )}

                      {/* Campaign History panel */}
                      {result.campaign_history &&
                        result.campaign_history !==
                          "No previous campaign data found for this advertiser." && (
                          <CollapsiblePanel
                            title="Campaign History"
                            defaultOpen={false}
                          >
                            <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                              {result.campaign_history}
                            </p>
                          </CollapsiblePanel>
                        )}

                      {/* Audience Segments & Reach panel */}
                      <AudienceSegmentsPanel data={result.audience_segments} />

                      {/* Google Trends panel */}
                      {result.google_trends && (
                        <CollapsiblePanel
                          title="Google Trends"
                          defaultOpen={false}
                        >
                          <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                            {result.google_trends}
                          </p>
                        </CollapsiblePanel>
                      )}

                      {/* Client Brief panel */}
                      {result.client_brief_summary &&
                        result.client_brief_summary !==
                          "No client brief provided." && (
                          <CollapsiblePanel
                            title="Client Brief"
                            defaultOpen={false}
                          >
                            <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
                              {result.client_brief_summary}
                            </p>
                          </CollapsiblePanel>
                        )}
                    </div>
                  );
                })()}

              {/* Export actions */}
              {result && !loading && (
                <div className="flex items-center gap-4 mt-6">
                  <button
                    onClick={() => {
                      track("Draft Email Clicked", {
                        has_samples: sampleCount > 0,
                        sample_count: sampleCount,
                      });
                      setDraftModalOpen(true);
                    }}
                    className="refractive-gradient px-6 py-3 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-all"
                  >
                    Draft Email
                  </button>
                  <button
                    onClick={async () => {
                      track("Download Deck Clicked", {
                        topic,
                        advertiser,
                        kpi,
                      });
                      setDeckLoading(true);
                      const startTime = Date.now();
                      try {
                        const res = await fetch("/api/download-deck", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          credentials: "include",
                          body: JSON.stringify({
                            content: result.content,
                            topic: topic.trim(),
                            advertiser: advertiser.trim(),
                            kpi,
                            audience_segments: result.audience_segments,
                          }),
                        });
                        if (!res.ok) {
                          const data = await res.json().catch(() => null);
                          throw new Error(
                            data?.detail || "Failed to generate deck",
                          );
                        }
                        const blob = await res.blob();
                        const filename =
                          res.headers
                            .get("content-disposition")
                            ?.match(/filename="(.+)"/)?.[1] ||
                          "Prism_Plan_Deck.pptx";
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        track("Deck Generated", {
                          topic,
                          advertiser,
                          kpi,
                          duration_ms: Date.now() - startTime,
                        });
                      } catch (err) {
                        const message =
                          err instanceof Error
                            ? err.message
                            : "Failed to generate deck";
                        setError(message);
                        track("Deck Download Failed", {
                          error_message: message,
                        });
                      } finally {
                        setDeckLoading(false);
                      }
                    }}
                    disabled={deckLoading}
                    className="refractive-gradient px-6 py-3 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {deckLoading ? "Generating..." : "Download Deck"}
                  </button>
                  <button
                    onClick={() => setSamplesModalOpen(true)}
                    className="text-sm text-on-surface-variant hover:text-accent-cyan transition-colors"
                  >
                    Writing style: {sampleCount} sample
                    {sampleCount !== 1 ? "s" : ""}
                  </button>
                </div>
              )}

              <DraftEmailModal
                open={draftModalOpen}
                onClose={() => setDraftModalOpen(false)}
                briefContent={result?.content || ""}
                topic={topic}
                advertiser={advertiser}
                kpi={kpi}
                sampleCount={sampleCount}
                onSampleCountChange={handleSampleCountChange}
                track={track}
              />

              <WritingSamplesModal
                open={samplesModalOpen}
                onClose={() => setSamplesModalOpen(false)}
                onSampleCountChange={handleSampleCountChange}
                track={track}
              />

              {/* Empty state */}
              {!result && !loading && !error && (
                <div className="text-center py-20">
                  <div className="inline-flex p-6 rounded-2xl bg-surface-container-high mb-6">
                    <svg
                      className="w-12 h-12 text-outline"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1}
                        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"
                      />
                    </svg>
                  </div>
                  <p className="text-slate-400 text-lg">
                    Enter a topic and advertiser to generate strategic insights.
                  </p>
                </div>
              )}
              {/* End of New Brief tab */}
            </>
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
        {expanded ? "Hide raw results" : `Show ${results.length} raw snippets`}
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
