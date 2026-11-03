"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";

export default function RegisterPage() {
  const { register, user, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/chat");
  }, [user, loading, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password);
      router.push("/chat");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="font-[family-name:var(--font-display)] text-4xl text-[var(--ink)]">
            NexusAI
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Create a free account — Gemini free tier only
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-[var(--border)] bg-[var(--panel)]/90 backdrop-blur p-6 space-y-4 shadow-sm"
        >
          <label className="block space-y-1.5">
            <span className="text-sm text-[var(--ink-soft)]">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm text-[var(--ink-soft)]">Password</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
            />
            <span className="text-xs text-[var(--muted)]">
              At least 8 characters, mix of letters and numbers/symbols
            </span>
          </label>

          {error ? (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-[var(--accent)] text-white py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-[var(--muted)]">
          Already have an account?{" "}
          <Link href="/login" className="text-[var(--accent)] font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
