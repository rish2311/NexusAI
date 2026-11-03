"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { MessageBubble } from "@/components/chat/MessageBubble";
import { useChatStream } from "@/hooks/useChatStream";
import type { ChatMessage, UsageInfo } from "@/types";

type LocalMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  usage?: UsageInfo | null;
  streaming?: boolean;
};

type Props = {
  threadId: string | null;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  onMessageComplete: () => void;
};

export function ChatPane({
  threadId,
  messages,
  loading,
  error,
  onMessageComplete,
}: Props) {
  const [input, setInput] = useState("");
  const [local, setLocal] = useState<LocalMessage[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { stream, stop, streaming } = useChatStream();

  useEffect(() => {
    setLocal(
      messages.map((m) => ({
        id: m.id,
        role: m.role as "user" | "assistant",
        content: m.content,
        usage: (m.metadata?.usage as UsageInfo | undefined) || null,
      })),
    );
    setStreamError(null);
  }, [messages, threadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [local, streaming]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!threadId || !input.trim() || streaming) return;

    const text = input.trim();
    setInput("");
    setStreamError(null);

    const userId = `local-user-${Date.now()}`;
    const asstId = `local-asst-${Date.now()}`;
    setLocal((prev) => [
      ...prev,
      { id: userId, role: "user", content: text },
      { id: asstId, role: "assistant", content: "", streaming: true },
    ]);

    await stream(
      {
        thread_id: threadId,
        message: text,
        idempotency_key: `web-${crypto.randomUUID()}`,
      },
      {
        onToken: (tok) => {
          setLocal((prev) =>
            prev.map((m) =>
              m.id === asstId ? { ...m, content: m.content + tok } : m,
            ),
          );
        },
        onDone: (done) => {
          setLocal((prev) =>
            prev.map((m) =>
              m.id === asstId
                ? {
                    ...m,
                    id: done.message_id,
                    streaming: false,
                    usage: done.usage,
                  }
                : m,
            ),
          );
          onMessageComplete();
        },
        onError: (code, message) => {
          setStreamError(
            code === "quota_exceeded"
              ? `Quota exceeded: ${message}`
              : message,
          );
          setLocal((prev) =>
            prev.map((m) =>
              m.id === asstId
                ? {
                    ...m,
                    streaming: false,
                    content: m.content || `(Error: ${message})`,
                  }
                : m,
            ),
          );
        },
      },
    );
  }

  if (!threadId) {
    return (
      <div className="flex h-full items-center justify-center text-[var(--muted)]">
        Select or create a conversation to begin.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-4">
        {loading ? (
          <p className="text-[var(--muted)] text-sm">Loading messages…</p>
        ) : error ? (
          <p className="text-red-600 text-sm">{error}</p>
        ) : local.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)] mb-2">
                Start chatting
              </h2>
              <p className="text-[var(--muted)] text-sm">
                Messages stream token-by-token from Gemini free tier. Usage and
                quotas appear after each reply.
              </p>
            </div>
          </div>
        ) : (
          local.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role}
              content={m.content}
              usage={m.usage}
              streaming={m.streaming}
            />
          ))
        )}
        {streamError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm">
            {streamError}
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={onSubmit}
        className="border-t border-[var(--border)] p-4 sm:px-8 bg-[var(--panel)]"
      >
        <div className="flex gap-2 items-end max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={1}
            placeholder="Message NexusAI…"
            className="flex-1 resize-none rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void onSubmit(e);
              }
            }}
          />
          {streaming ? (
            <button
              type="button"
              onClick={() => void stop()}
              className="rounded-xl border border-[var(--border)] px-4 py-3 text-sm font-medium text-[var(--ink)] hover:bg-[var(--surface)]"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="rounded-xl bg-[var(--accent)] text-white px-5 py-3 text-sm font-medium disabled:opacity-40 hover:opacity-90"
            >
              Send
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
