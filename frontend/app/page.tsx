"use client";

import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Button from "@/components/Button";
import StatusDot from "@/components/StatusDot";
import SectionHeading from "@/components/SectionHeading";
import Link from "next/link";
import { useAnalytics } from "@/components/AnalyticsProvider";
import { DATA_SOURCES, DATA_SOURCES_HEADING } from "@/lib/landingContent";

export default function LandingPage() {
  const { track } = useAnalytics();

  function trackCta(ctaName: string) {
    track("CTA Clicked", { cta_name: ctaName });
  }

  return (
    <>
      <Navbar />

      {/* Hero Section */}
      <header className="relative pt-44 pb-32 px-8 overflow-hidden min-h-screen flex items-center">
        {/* Decorative glow */}
        <div className="absolute top-1/4 -right-20 w-[500px] h-[500px] bg-primary/20 blur-[120px] rounded-full pointer-events-none" />

        <div className="max-w-screen-2xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-16 items-center relative z-10 w-full">
          <div className="lg:col-span-7">
            <StatusDot label="Beta" />
            <h1 className="font-headline text-6xl md:text-8xl font-extrabold tracking-tighter leading-[0.95] mb-8 mt-8">
              The <span className="text-accent-cyan italic">3D View</span> Of
              <br />
              Your Audience
            </h1>
            <p className="text-xl md:text-2xl text-slate-400 max-w-2xl font-light leading-relaxed mb-12">
              The 1st party planning tool that draws on our extensive
              behavioural data, in house research, advertiser understanding and
              deep editorial expertise for{" "}
              <span className="text-accent-cyan font-medium">
                tailored recommendations
              </span>{" "}
              on every brief.
            </p>
            <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-6">
              <Link href="/app" onClick={() => trackCta("Explore Topic")}>
                <Button variant="primary" className="text-lg">
                  Explore Topic
                </Button>
              </Link>
              <Button
                variant="secondary"
                className="text-lg"
                onClick={() => trackCta("Watch Demo")}
              >
                Watch Demo
              </Button>
            </div>
          </div>

          {/* 3D Cube */}
          <div className="lg:col-span-5 relative flex items-center justify-center">
            <div className="animate-float relative">
              <img
                src="/cube.png"
                alt="Prism Plan cube"
                className="monolith-cube w-full max-w-[420px]"
              />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-primary/20 blur-[120px] rounded-full -z-10" />
            </div>
          </div>
        </div>
      </header>

      {/* Features */}
      <section
        id="features"
        className="py-32 px-8 bg-surface-container-low border-y border-white/5 relative overflow-hidden"
      >
        <div className="max-w-screen-2xl mx-auto relative z-10">
          <SectionHeading>
            Data-Driven <br />
            Planning.
          </SectionHeading>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Editorial Intelligence */}
            <div className="group bg-surface-container-lowest p-10 rounded-2xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 relative overflow-hidden">
              <div className="mb-8 inline-flex p-4 rounded-xl bg-accent-cyan/10 text-accent-cyan group-hover:bg-accent-cyan group-hover:text-white transition-colors relative z-10">
                <svg
                  className="w-8 h-8"
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
              <h3 className="font-headline text-2xl font-bold mb-4 relative z-10">
                Editorial Intelligence
              </h3>
              <p className="text-slate-400 leading-relaxed relative z-10">
                Draws on in-house editorial expertise and transcripts to surface
                the themes and angles that resonate with your audience.
              </p>
            </div>

            {/* Brand Research — elevated */}
            <div className="group bg-surface-container-highest p-10 rounded-2xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 transform lg:scale-105 shadow-2xl relative overflow-hidden">
              <div className="mb-8 inline-flex p-4 rounded-xl bg-accent-cyan/10 text-accent-cyan group-hover:bg-accent-cyan group-hover:text-white transition-colors relative z-10">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                  />
                </svg>
              </div>
              <h3 className="font-headline text-2xl font-bold mb-4 relative z-10">
                Brand Research
              </h3>
              <p className="text-slate-400 leading-relaxed relative z-10">
                Automated advertiser analysis via web research, uncovering brand
                positioning, campaigns, and market context.
              </p>
            </div>

            {/* Audience & Trends */}
            <div className="group bg-surface-container-lowest p-10 rounded-2xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 relative overflow-hidden">
              <div className="mb-8 inline-flex p-4 rounded-xl bg-accent-cyan/10 text-accent-cyan group-hover:bg-accent-cyan group-hover:text-white transition-colors relative z-10">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                  />
                </svg>
              </div>
              <h3 className="font-headline text-2xl font-bold mb-4 relative z-10">
                Audience Behaviour
              </h3>
              <p className="text-slate-400 leading-relaxed relative z-10">
                First-party behavioural data to identify which segments to
                reach, at what scale, and when they are most engaged.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Data Sources Showcase */}
      <section className="py-32 px-8">
        <div className="max-w-screen-2xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
            <div>
              <h2 className="text-4xl md:text-5xl font-headline font-bold leading-tight mb-6">
                {DATA_SOURCES_HEADING}
              </h2>
              <p className="text-xl text-slate-400 leading-relaxed">
                Every Prism Plan synthesises brand intelligence, audience
                behaviour, format benchmarks, and campaign history into a
                single, actionable advertising recommendation.
              </p>
            </div>

            {/* Data source cards */}
            <div className="grid grid-cols-2 gap-8">
              {DATA_SOURCES.map((source) => (
                <div
                  key={source.title}
                  className="p-6 bg-surface-container-low rounded-xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-300"
                >
                  {/*
                   * Titles carry soft hyphens because this grid stays two-up on
                   * a phone — see `SHY` in `lib/landingContent.ts`. break-words
                   * is the backstop for a narrower phone still, where even a
                   * syllable overruns.
                   */}
                  <h4 className="font-headline font-bold text-lg mb-2 break-words">
                    {source.title}
                  </h4>
                  <p className="text-slate-500 text-sm leading-relaxed">
                    {source.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-32 px-8 overflow-hidden relative">
        <div className="absolute inset-0 bg-primary/20 -skew-y-6 translate-y-24" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="font-headline text-5xl md:text-7xl font-extrabold tracking-tight mb-8">
            Build your Prism Plan
          </h2>
          <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto">
            Turn editorial insight, audience data, and brand research into
            actionable strategy in seconds.
          </p>
          <Link href="/app" onClick={() => trackCta("Get Started")}>
            <Button variant="primary" className="text-xl px-12 py-6">
              Get Started
            </Button>
          </Link>
        </div>
      </section>

      <Footer />
    </>
  );
}
