"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import Button from "@/components/Button";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Something went wrong");
      }
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />
      <main className="min-h-screen flex items-center justify-center px-8 pt-32 pb-16">
        <GlassCard className="w-full max-w-md p-8">
          <h1 className="font-headline text-3xl font-bold tracking-tight text-white mb-2">
            Reset your password
          </h1>

          {sent ? (
            <>
              <p className="text-slate-400 mb-6">
                If an account exists with that email, we&apos;ve sent a reset link.
                Check your inbox.
              </p>
              <Link href="/login" className="text-accent-cyan hover:underline text-sm">
                Back to login
              </Link>
            </>
          ) : (
            <>
              <p className="text-slate-400 mb-8">
                Enter your email and we&apos;ll send you a link to reset your password.
              </p>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-6 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="email" className="block text-sm font-semibold text-slate-300 mb-2">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-surface-container-highest border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-colors"
                    placeholder="jane@company.com"
                  />
                </div>

                <Button type="submit" disabled={loading} className="w-full">
                  {loading ? "Sending..." : "Send reset link"}
                </Button>
              </form>

              <p className="text-slate-400 text-sm text-center mt-6">
                <Link href="/login" className="text-accent-cyan hover:underline">
                  Back to login
                </Link>
              </p>
            </>
          )}
        </GlassCard>
      </main>
      <Footer />
    </>
  );
}
