"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { useAnalytics } from "@/components/AnalyticsProvider";

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const { track } = useAnalytics();

  function trackNav(linkName: string) {
    track("Nav Link Clicked", { link_name: linkName });
  }

  return (
    <nav className="fixed top-0 w-full z-50 bg-[#0a0c10]/80 backdrop-blur-[20px] border-b border-white/5 shadow-2xl">
      <div className="flex justify-between items-center px-8 py-5 max-w-screen-2xl mx-auto">
        <Link
          href="/"
          onClick={() => trackNav("Logo")}
          className="text-2xl font-bold tracking-tighter text-white font-headline flex items-center gap-2"
        >
          <span className="w-2 h-6 bg-accent-cyan rounded-full" />
          Prism Plan
        </Link>

        <div className="flex items-center space-x-6">
          <Link
            href="/#features"
            onClick={() => trackNav("Features")}
            className="hidden md:inline text-slate-400 hover:text-white transition-all duration-300 font-headline font-semibold tracking-tight"
          >
            Features
          </Link>
          <Link
            href="/assistant"
            onClick={() => trackNav("Assistant")}
            className="hidden md:inline text-slate-400 hover:text-white transition-all duration-300 font-headline font-semibold tracking-tight"
          >
            Assistant
          </Link>
          <Link
            href="/tetris"
            onClick={() => trackNav("Prism Play")}
            className="hidden md:inline text-slate-400 hover:text-white transition-all duration-300 font-headline font-semibold tracking-tight"
          >
            Prism Play
          </Link>
          {loading ? null : user ? (
            <>
              <span className="text-slate-300 font-semibold text-sm">
                {user.name}
              </span>
              <button
                onClick={() => {
                  trackNav("Logout");
                  logout();
                }}
                className="text-slate-400 font-semibold hover:text-white active:scale-95 transition-all"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                onClick={() => trackNav("Login")}
                className="text-slate-400 font-semibold hover:text-white active:scale-95 transition-all"
              >
                Login
              </Link>
              <Link
                href="/app"
                onClick={() => trackNav("Launch App")}
                className="refractive-gradient px-6 py-2.5 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-transform inline-block"
              >
                Launch App
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
