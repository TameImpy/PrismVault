"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import Button from "@/components/Button";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/app";
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      router.push(redirect);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
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
            Welcome back
          </h1>
          <p className="text-slate-400 mb-8">
            Log in to access the Prism Data Vault insights tool.
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

            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-slate-300 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-surface-container-highest border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-colors"
                placeholder="Your password"
              />
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Logging in..." : "Log in"}
            </Button>
          </form>

          <p className="text-slate-400 text-sm text-center mt-4">
            <Link href="/forgot-password" className="text-accent-cyan hover:underline">
              Forgot password?
            </Link>
          </p>

          <p className="text-slate-400 text-sm text-center mt-3">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-accent-cyan hover:underline">
              Sign up
            </Link>
          </p>
        </GlassCard>
      </main>
      <Footer />
    </>
  );
}
