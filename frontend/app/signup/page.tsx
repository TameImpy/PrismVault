"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import Button from "@/components/Button";
import { useAuth } from "@/contexts/AuthContext";
import { completeSignIn, signedInDestination } from "@/lib/authNavigation";

export default function SignupPage() {
  const router = useRouter();
  const { user, loading: authLoading, signup } = useAuth();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // As on the login page (#161): signing up already leaves you signed in, so
  // this form must not be what a Back press or a bookmark hands you back.
  const destination = signedInDestination({
    loading: authLoading,
    signedIn: Boolean(user),
  });

  useEffect(() => {
    if (destination) router.replace(destination);
  }, [destination, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signup(email, name, password);
      completeSignIn(window.location, null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  if (authLoading || destination) return null;

  return (
    <>
      <Navbar />
      <main className="min-h-screen flex items-center justify-center px-8 pt-32 pb-16">
        <GlassCard className="w-full max-w-md p-8">
          <h1 className="font-headline text-3xl font-bold tracking-tight text-white mb-2">
            Create an account
          </h1>
          <p className="text-slate-400 mb-8">
            Sign up to access the Prism Data Vault insights tool. Accounts are
            limited to <span className="text-slate-300">@immediate.co.uk</span>{" "}
            email addresses.
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-6 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-semibold text-slate-300 mb-2"
              >
                Full name
              </label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-surface-container-highest border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-colors"
                placeholder="Jane Smith"
              />
            </div>

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-semibold text-slate-300 mb-2"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-surface-container-highest border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-accent-cyan transition-colors"
                placeholder="jane.smith@immediate.co.uk"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-semibold text-slate-300 mb-2"
              >
                Password
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

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Creating account..." : "Create account"}
            </Button>
          </form>

          <p className="text-slate-400 text-sm text-center mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-accent-cyan hover:underline">
              Log in
            </Link>
          </p>
        </GlassCard>
      </main>
      <Footer />
    </>
  );
}
