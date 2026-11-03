"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { getApiUrl } from "@/services/api";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/chat" : "/login");
  }, [user, loading, router]);

  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-3">
        <h1 className="font-[family-name:var(--font-display)] text-4xl text-[var(--ink)]">
          NexusAI
        </h1>
        <p className="text-sm text-[var(--muted)]">Loading…</p>
        <p className="text-xs text-[var(--muted)]">API: {getApiUrl()}</p>
      </div>
    </main>
  );
}
