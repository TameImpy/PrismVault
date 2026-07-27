"use client";

import ReactMarkdown from "react-markdown";

/**
 * Historical Research hero card (PRD #125 / slice #127).
 *
 * The "panel is the hero" surface for the proprietary-research pull-through.
 * Composes two things:
 *   1. Deterministic frontmatter metadata (source title, organisation,
 *      fieldwork dates, respondent base, "matched on") passed verbatim from the
 *      backend `historical_research` dict — no hallucination risk.
 *   2. The model-generated, brief-tailored findings bullets, parsed from the
 *      `## Historical Research` output section and passed in as `content`.
 *
 * Renders ONLY when `data.relevant === true` — mirroring the conditional render
 * used for campaign_history. On a non-matching brief the backend sends
 * `{ relevant: false }` and this component returns null (no empty box).
 */
export interface HistoricalResearch {
  relevant: boolean;
  /**
   * Filename of the matched research file. Not rendered here — it rides along
   * so the deck download can name the source whose body the server re-reads
   * when grounding its insights. Absent when nothing matched.
   */
  file?: string;
  title?: string;
  organisation?: string;
  fieldwork?: string;
  total_respondents?: number;
  matched_on?: string[];
}

const bulletMarkdownComponents = {
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
  ul: ({ children, ...props }: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="list-disc list-inside space-y-2 mb-0" {...props}>
      {children}
    </ul>
  ),
  p: ({ children, ...props }: React.ComponentPropsWithoutRef<"p">) => (
    <p className="mb-3 last:mb-0" {...props}>
      {children}
    </p>
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

export default function HistoricalResearchCard({
  data,
  content,
}: {
  data?: HistoricalResearch;
  content?: string;
}) {
  // Conditional render: only ever appears on a relevant (matched) brief.
  if (!data || !data.relevant) return null;

  return (
    <div className="bg-surface-container-lowest rounded-2xl p-8 border border-white/5 border-l-4 border-l-accent-cyan hover:border-accent-cyan/20 transition-all duration-500">
      <div className="flex items-center gap-3 mb-2">
        <div className="inline-flex p-3 rounded-xl bg-accent-cyan/10 text-accent-cyan">
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
              d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
            />
          </svg>
        </div>
        <span className="text-[10px] font-bold tracking-widest text-accent-cyan uppercase">
          Proprietary Research
        </span>
      </div>

      <h2 className="font-headline text-2xl font-bold mb-4">
        Historical Research
      </h2>

      {/* Verbatim frontmatter metadata — provenance the salesperson can cite. */}
      <div className="rounded-xl border border-white/10 bg-surface-container px-4 py-3 mb-5 space-y-1">
        {data.title && (
          <p className="text-on-surface text-sm font-semibold">{data.title}</p>
        )}
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-on-surface-variant text-xs">
          {data.organisation && (
            <span>
              Source:{" "}
              <span className="text-on-surface">{data.organisation}</span>
            </span>
          )}
          {data.fieldwork && (
            <span>
              Fieldwork:{" "}
              <span className="text-on-surface">{data.fieldwork}</span>
            </span>
          )}
          {typeof data.total_respondents === "number" && (
            <span>
              Respondent base:{" "}
              <span className="text-on-surface tabular-nums">
                n={data.total_respondents.toLocaleString("en-GB")}
              </span>
            </span>
          )}
        </div>
        {data.matched_on && data.matched_on.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-1.5">
            <span className="text-on-surface-variant text-xs">Matched on:</span>
            {data.matched_on.map((kw) => (
              <span
                key={kw}
                className="rounded-full bg-surface-container-highest text-accent-cyan text-[11px] font-medium px-2.5 py-0.5"
              >
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Model-generated, brief-tailored findings bullets. */}
      {content && (
        <div className="text-on-surface-variant text-sm leading-relaxed break-words-anywhere">
          <ReactMarkdown components={bulletMarkdownComponents}>
            {content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
