"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import Button from "@/components/Button";

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Failed to reset password");
      }
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <>
        <Navbar />
        <main className="min-h-screen flex items-center justify-center px-8 pt-32 pb-16">
          <GlassCard className="w-full max-w-md p-8">
            <h1 className="font-headline text-3xl font-bold tracking-tight text-white mb-4">
              Invalid reset link
            </h1>
            <p className="text-slate-400 mb-6">
              This reset link is missing or invalid. Please request a new one.
            </p>
            <Link href="/forgot-password" className="text-accent-cyan hover:underline text-sm">
              Request a new reset link
            </Link>
          </GlassCard>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="min-h-screen flex items-center justify-center px-8 pt-32 pb-16">
        <GlassCard className="w-full max-w-md p-8">
          <h1 className="font-headline text-3xl font-bold tracking-tight text-white mb-2">
            Set new password
          </h1>
          <p className="text-slate-400 mb-8">
            Enter your new password below.
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-6 text-red-400 text-sm">
              {error}
              {(error.includes("expired") || error.includes("Invalid")) && (
                <span className="block mt-2">
                  <Link href="/forgot-password" className="text-accent-cyan hover:underline">
                    Request a new reset link
                  </Link>
                </span>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-slate-300 mb-2">
                New password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-surface-container-highest border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-colors"
                placeholder="At least 8 characters"
              />
            </div>

            <div>
              <label htmlFor="confirm" className="block text-sm font-semibold text-slate-300 mb-2">
                Confirm password
              </label>
              <input
                id="confirm"
                type="password"
                required
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-surface-container-highest border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-colors"
                placeholder="Type your password again"
              />
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Resetting..." : "Reset password"}
            </Button>
          </form>

          <p className="text-slate-400 text-sm text-center mt-6">
            <Link href="/login" className="text-accent-cyan hover:underline">
              Back to login
            </Link>
          </p>
        </GlassCard>
      </main>
      <Footer />
    </>
  );
}
