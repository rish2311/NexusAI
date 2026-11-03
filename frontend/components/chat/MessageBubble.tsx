"use client";

import type { UsageInfo } from "@/types";

type Props = {
  role: "user" | "assistant" | "system";
  content: string;
  usage?: UsageInfo | null;
  streaming?: boolean;
};

export function MessageBubble({ role, content, usage, streaming }: Props) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed ${
          isUser
            ? "bg-[var(--accent)] text-white"
            : "bg-[var(--surface)] text-[var(--ink)] border border-[var(--border)]"
        }`}
      >
        <div className="whitespace-pre-wrap break-words">
          {content}
          {streaming ? <span className="inline-block w-2 h-4 ml-0.5 bg-current animate-pulse align-middle" /> : null}
        </div>
        {usage && !streaming ? (
          <div className="mt-3 pt-2 border-t border-[var(--border)] flex flex-wrap gap-2 text-xs text-[var(--muted)]">
            <span className="inline-flex items-center rounded px-1.5 py-0.5 bg-[var(--free-badge)] text-[var(--free-badge-ink)] font-medium">
              {usage.tier}
            </span>
            <span>
              {usage.input_tokens + usage.output_tokens} tokens · {usage.provider}/{usage.model}
            </span>
            {usage.estimated_commercial_cost_usd > 0 ? (
              <span>~${usage.estimated_commercial_cost_usd.toFixed(6)} est.</span>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
