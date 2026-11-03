"use client";

import type { Thread } from "@/types";

type Props = {
  threads: Thread[];
  activeId: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onLogout: () => void;
  email?: string;
};

export function ThreadSidebar({
  threads,
  activeId,
  loading,
  error,
  onSelect,
  onCreate,
  onDelete,
  onLogout,
  email,
}: Props) {
  return (
    <aside className="flex h-full w-full flex-col border-r border-[var(--border)] bg-[var(--sidebar)]">
      <div className="p-4 border-b border-[var(--border)]">
        <div className="font-[family-name:var(--font-display)] text-xl tracking-tight text-[var(--ink)]">
          NexusAI
        </div>
        <p className="text-xs text-[var(--muted)] mt-1 truncate">{email}</p>
      </div>

      <div className="p-3">
        <button
          type="button"
          onClick={onCreate}
          className="w-full rounded-xl bg-[var(--accent)] text-white py-2.5 text-sm font-medium hover:opacity-90 transition"
        >
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading ? (
          <p className="text-sm text-[var(--muted)] px-2 py-4">Loading threads…</p>
        ) : error ? (
          <p className="text-sm text-red-600 px-2 py-4">{error}</p>
        ) : threads.length === 0 ? (
          <p className="text-sm text-[var(--muted)] px-2 py-4">No conversations yet.</p>
        ) : (
          <ul className="space-y-1">
            {threads.map((t) => (
              <li key={t.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(t.id)}
                  className={`w-full text-left rounded-lg px-3 py-2.5 text-sm truncate transition ${
                    activeId === t.id
                      ? "bg-[var(--surface-strong)] text-[var(--ink)]"
                      : "text-[var(--ink-soft)] hover:bg-[var(--surface)]"
                  }`}
                >
                  {t.title}
                </button>
                <button
                  type="button"
                  aria-label="Delete thread"
                  onClick={() => onDelete(t.id)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-[var(--muted)] hover:text-red-600 text-xs px-1"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="p-3 border-t border-[var(--border)]">
        <button
          type="button"
          onClick={onLogout}
          className="w-full rounded-lg border border-[var(--border)] py-2 text-sm text-[var(--ink-soft)] hover:bg-[var(--surface)]"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
