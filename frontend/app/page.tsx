import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Button from "@/components/Button";
import StatusDot from "@/components/StatusDot";
import SectionHeading from "@/components/SectionHeading";
import Link from "next/link";

export default function LandingPage() {
  return (
    <>
      <Navbar />

      {/* Hero Section */}
      <header className="relative pt-44 pb-32 px-8 overflow-hidden min-h-screen flex items-center">
        {/* Decorative glow */}
        <div className="absolute top-1/4 -right-20 w-[500px] h-[500px] bg-primary/20 blur-[120px] rounded-full pointer-events-none" />

        <div className="max-w-screen-2xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-16 items-center relative z-10 w-full">
          <div className="lg:col-span-7">
            <StatusDot label="v2.4 Deployed" />
            <h1 className="font-headline text-6xl md:text-8xl font-extrabold tracking-tighter leading-[0.95] mb-8 mt-8">
              The <span className="text-accent-cyan italic">3D View</span> Of
              <br />Your Audience
            </h1>
            <p className="text-xl md:text-2xl text-slate-400 max-w-2xl font-light leading-relaxed mb-12">
              Tap into our proprietary vault of deep editorial expertise,
              behavioural data, panel research and more for unique insight and
              guidance on how to reach and message your audience.
            </p>
            <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-6">
              <Link href="/app">
                <Button variant="primary" className="text-lg">
                  Explore Topic
                </Button>
              </Link>
              <Button variant="secondary" className="text-lg">
                Watch Demo
              </Button>
            </div>
          </div>

          {/* 3D Cube */}
          <div className="lg:col-span-5 relative flex items-center justify-center">
            <div className="animate-float relative">
              <img
                src="/cube.png"
                alt="Refractive Monolith Cube"
                className="monolith-cube w-full max-w-[420px]"
              />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-primary/20 blur-[120px] rounded-full -z-10" />
            </div>
          </div>
        </div>
      </header>

      {/* Feature Bento Grid */}
      <section className="py-32 px-8 bg-surface-container-low border-y border-white/5 relative overflow-hidden">
        <div className="max-w-screen-2xl mx-auto relative z-10">
          <SectionHeading>
            Precision-Engineered <br />
            Capabilities.
          </SectionHeading>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="group bg-surface-container-lowest p-10 rounded-2xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 relative overflow-hidden">
              <div className="mb-8 inline-flex p-4 rounded-xl bg-accent-cyan/10 text-accent-cyan group-hover:bg-accent-cyan group-hover:text-white transition-colors relative z-10">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <h3 className="font-headline text-2xl font-bold mb-4 relative z-10">
                Real-time Analytics
              </h3>
              <p className="text-slate-400 leading-relaxed relative z-10">
                Latency-free data streaming across global nodes with millisecond
                accuracy and refractive processing.
              </p>
            </div>

            {/* Feature 2 — elevated */}
            <div className="group bg-surface-container-highest p-10 rounded-2xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 transform lg:scale-105 shadow-2xl relative overflow-hidden">
              <div className="mb-8 inline-flex p-4 rounded-xl bg-accent-cyan/10 text-accent-cyan group-hover:bg-accent-cyan group-hover:text-white transition-colors relative z-10">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
              </div>
              <h3 className="font-headline text-2xl font-bold mb-4 relative z-10">
                Secure Vaulting
              </h3>
              <p className="text-slate-400 leading-relaxed relative z-10">
                Quantum-resistant encryption layers that wrap your data in an
                impenetrable deep-sea security shell.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group bg-surface-container-lowest p-10 rounded-2xl border border-white/5 hover:border-accent-cyan/20 transition-all duration-500 relative overflow-hidden">
              <div className="mb-8 inline-flex p-4 rounded-xl bg-accent-cyan/10 text-accent-cyan group-hover:bg-accent-cyan group-hover:text-white transition-colors relative z-10">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
              </div>
              <h3 className="font-headline text-2xl font-bold mb-4 relative z-10">
                AI-Powered Insights
              </h3>
              <p className="text-slate-400 leading-relaxed relative z-10">
                Self-learning algorithms that predict data bottlenecks before
                they happen, optimizing your entire ecosystem.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section className="py-32 px-8">
        <div className="max-w-screen-2xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
            <div>
              <svg
                className="text-accent-cyan w-16 h-16 mb-8"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zM0 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151C7.546 6.068 5.983 8.789 5.983 11h4v10H0z" />
              </svg>
              <blockquote className="text-4xl md:text-5xl font-headline font-bold leading-tight mb-10">
                &ldquo;Prism changed how we perceive data. It&rsquo;s no longer
                just a resource; it&rsquo;s our primary competitive
                advantage.&rdquo;
              </blockquote>
              <div className="flex items-center space-x-4">
                <div className="w-16 h-16 rounded-full bg-surface-container-high border border-white/10 flex items-center justify-center text-accent-cyan font-headline font-bold text-xl">
                  ES
                </div>
                <div>
                  <p className="font-headline font-bold text-lg">
                    Elena Sterling
                  </p>
                  <p className="text-accent-cyan text-[10px] font-bold tracking-[0.2em] uppercase">
                    CTO, NexaCorp Enterprise
                  </p>
                </div>
              </div>
            </div>

            {/* Partner logos grid */}
            <div className="grid grid-cols-2 gap-8">
              {["GLOBAL_CORE", "AETHER_UI", "SYNTH_SYS", "PRISM_FLOW"].map(
                (name) => (
                  <div
                    key={name}
                    className="h-32 flex items-center justify-center grayscale opacity-30 hover:opacity-100 hover:grayscale-0 transition-all bg-surface-container-low rounded-xl border border-white/5 overflow-hidden group"
                  >
                    <span className="font-headline font-black text-2xl tracking-tighter relative z-10">
                      {name}
                    </span>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-32 px-8 bg-surface-container-lowest">
        <div className="max-w-screen-2xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="font-headline text-5xl font-extrabold mb-6">
              Tailored Performance
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Choose the clarity level that matches your organizational scale.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
            {/* Essential */}
            <div className="p-12 bg-surface-container border-r border-white/5 flex flex-col">
              <h3 className="text-xl font-headline font-bold mb-2">
                Essential
              </h3>
              <p className="text-slate-500 text-sm mb-8">For emerging teams</p>
              <div className="mb-10">
                <span className="text-5xl font-headline font-bold">$49</span>
                <span className="text-outline">/mo</span>
              </div>
              <ul className="space-y-4 mb-12 flex-grow">
                {["1TB Secure Storage", "Basic Analytics", "Email Support"].map(
                  (item) => (
                    <li
                      key={item}
                      className="flex items-center space-x-3 text-slate-400"
                    >
                      <svg className="w-4 h-4 text-accent-cyan flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span>{item}</span>
                    </li>
                  )
                )}
              </ul>
              <button className="w-full py-4 border border-white/10 rounded-xl font-bold hover:bg-surface-bright transition-colors">
                Select Essential
              </button>
            </div>

            {/* Professional */}
            <div className="p-12 bg-surface-container-high border-r border-white/5 flex flex-col relative overflow-hidden">
              <div className="absolute top-4 right-12 bg-accent-cyan text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-widest">
                Recommended
              </div>
              <h3 className="text-xl font-headline font-bold mb-2">
                Professional
              </h3>
              <p className="text-slate-500 text-sm mb-8">
                For scaling organizations
              </p>
              <div className="mb-10">
                <span className="text-5xl font-headline font-bold">$199</span>
                <span className="text-outline">/mo</span>
              </div>
              <ul className="space-y-4 mb-12 flex-grow">
                {[
                  "Unlimited Storage",
                  "Advanced AI Insights",
                  "API Access",
                  "24/7 Priority Support",
                ].map((item) => (
                  <li key={item} className="flex items-center space-x-3">
                    <svg className="w-4 h-4 text-accent-cyan flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <button className="w-full py-4 refractive-gradient rounded-xl font-bold text-white shadow-lg">
                Scale Up Now
              </button>
            </div>

            {/* Enterprise */}
            <div className="p-12 bg-surface-container flex flex-col">
              <h3 className="text-xl font-headline font-bold mb-2">
                Enterprise
              </h3>
              <p className="text-slate-500 text-sm mb-8">
                For global infrastructure
              </p>
              <div className="mb-10">
                <span className="text-5xl font-headline font-bold">Custom</span>
              </div>
              <ul className="space-y-4 mb-12 flex-grow">
                {[
                  "Dedicated Nodes",
                  "SLA Guarantees",
                  "Custom Integrations",
                ].map((item) => (
                  <li
                    key={item}
                    className="flex items-center space-x-3 text-slate-400"
                  >
                    <svg className="w-4 h-4 text-accent-cyan flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <button className="w-full py-4 border border-white/10 rounded-xl font-bold hover:bg-surface-bright transition-colors">
                Contact Sales
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-32 px-8 overflow-hidden relative">
        <div className="absolute inset-0 bg-primary/20 -skew-y-6 translate-y-24" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="font-headline text-5xl md:text-7xl font-extrabold tracking-tight mb-8">
            Ready to Secure Your Future?
          </h2>
          <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto">
            Join 10,000+ architects who have traded data complexity for
            architectural clarity.
          </p>
          <div className="inline-flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-6">
            <Link href="/app">
              <Button variant="primary" className="text-xl px-12 py-6">
                Get Started Free
              </Button>
            </Link>
            <Button variant="secondary" className="text-xl px-12 py-6 backdrop-blur-sm">
              Talk to an Architect
            </Button>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
