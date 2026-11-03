"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { ChatPane } from "@/components/chat/ChatPane";
import { ThreadSidebar } from "@/components/chat/ThreadSidebar";
import { threadsApi } from "@/services/api";
import type { ChatMessage, Thread } from "@/types";

export default function ChatPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();

  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [user, authLoading, router]);

  const loadThreads = useCallback(async () => {
    setThreadsLoading(true);
    setThreadsError(null);
    try {
      const list = await threadsApi.list();
      setThreads(list);
      if (!activeId && list.length > 0) setActiveId(list[0].id);
    } catch (err) {
      setThreadsError((err as Error).message);
    } finally {
      setThreadsLoading(false);
    }
  }, [activeId]);

  const loadMessages = useCallback(async (threadId: string) => {
    setMessagesLoading(true);
    setMessagesError(null);
    try {
      const data = await threadsApi.messages(threadId);
      setMessages(data.items);
    } catch (err) {
      setMessagesError((err as Error).message);
      setMessages([]);
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void loadThreads();
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (activeId) void loadMessages(activeId);
    else setMessages([]);
  }, [activeId, loadMessages]);

  async function handleCreate() {
    try {
      const t = await threadsApi.create("New chat");
      setThreads((prev) => [t, ...prev]);
      setActiveId(t.id);
      setMobileOpen(false);
    } catch (err) {
      setThreadsError((err as Error).message);
    }
  }

  async function handleDelete(id: string) {
    try {
      await threadsApi.remove(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (err) {
      setThreadsError((err as Error).message);
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  if (authLoading || !user) {
    return (
      <main className="min-h-screen flex items-center justify-center text-[var(--muted)]">
        Loading…
      </main>
    );
  }

  return (
    <main className="h-screen flex overflow-hidden">
      <div
        className={`${
          mobileOpen ? "fixed inset-0 z-40 flex" : "hidden"
        } md:static md:flex md:w-72 lg:w-80 shrink-0`}
      >
        {mobileOpen ? (
          <button
            type="button"
            className="absolute inset-0 bg-black/30 md:hidden"
            aria-label="Close sidebar"
            onClick={() => setMobileOpen(false)}
          />
        ) : null}
        <div className="relative z-10 w-72 max-w-[85vw] h-full md:w-full">
          <ThreadSidebar
            threads={threads}
            activeId={activeId}
            loading={threadsLoading}
            error={threadsError}
            email={user.email}
            onSelect={(id) => {
              setActiveId(id);
              setMobileOpen(false);
            }}
            onCreate={() => void handleCreate()}
            onDelete={(id) => void handleDelete(id)}
            onLogout={() => void handleLogout()}
          />
        </div>
      </div>

      <section className="flex-1 flex flex-col min-w-0 bg-[var(--panel)]/60">
        <div className="md:hidden flex items-center gap-3 border-b border-[var(--border)] px-4 py-3">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm"
          >
            Threads
          </button>
          <span className="font-[family-name:var(--font-display)] text-lg">NexusAI</span>
        </div>
        <ChatPane
          threadId={activeId}
          messages={messages}
          loading={messagesLoading}
          error={messagesError}
          onMessageComplete={() => {
            if (activeId) void loadMessages(activeId);
            void loadThreads();
          }}
        />
      </section>
    </main>
  );
}
