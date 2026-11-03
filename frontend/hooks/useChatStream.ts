"use client";

import { useCallback, useRef, useState } from "react";

import { getAccessToken, getApiUrl, getRefreshToken, setTokens } from "@/services/api";
import type { StreamDone, TokenPair } from "@/types";

type StreamHandlers = {
  onToken: (text: string) => void;
  onDone: (done: StreamDone) => void;
  onError: (code: string, message: string) => void;
  onRunId?: (runId: string) => void;
};

export function useChatStream() {
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const runIdRef = useRef<string | null>(null);

  const stop = useCallback(async () => {
    abortRef.current?.abort();
    const runId = runIdRef.current;
    if (runId) {
      const token = getAccessToken();
      try {
        await fetch(`${getApiUrl()}/v1/chat/stop`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ run_id: runId }),
        });
      } catch {
        /* ignore */
      }
    }
    setStreaming(false);
  }, []);

  const stream = useCallback(
    async (
      body: { thread_id: string; message: string; idempotency_key: string },
      handlers: StreamHandlers,
    ) => {
      setStreaming(true);
      abortRef.current = new AbortController();
      runIdRef.current = null;

      const doFetch = async (access: string | null) => {
        return fetch(`${getApiUrl()}/v1/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(access ? { Authorization: `Bearer ${access}` } : {}),
          },
          body: JSON.stringify(body),
          signal: abortRef.current?.signal,
        });
      };

      try {
        let res = await doFetch(getAccessToken());
        if (res.status === 401) {
          const refresh = getRefreshToken();
          if (refresh) {
            const refreshRes = await fetch(`${getApiUrl()}/v1/auth/refresh`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: refresh }),
            });
            if (refreshRes.ok) {
              const tokens = (await refreshRes.json()) as TokenPair;
              setTokens(tokens);
              res = await doFetch(tokens.access_token);
            }
          }
        }

        if (!res.ok) {
          let message = res.statusText;
          let code = "http_error";
          try {
            const err = await res.json();
            if (typeof err.detail === "object" && err.detail?.code) {
              code = err.detail.code;
              message = err.detail.message || message;
            } else if (typeof err.detail === "string") {
              message = err.detail;
            }
          } catch {
            /* ignore */
          }
          handlers.onError(code, message);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          handlers.onError("stream_error", "No response body");
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let eventName = "message";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n");
          buffer = parts.pop() || "";

          for (const line of parts) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const raw = line.slice(5).trim();
              try {
                const data = JSON.parse(raw);
                if (eventName === "token") handlers.onToken(data.text || "");
                else if (eventName === "done") handlers.onDone(data as StreamDone);
                else if (eventName === "error")
                  handlers.onError(data.code || "error", data.message || "Error");
                else if (eventName === "run") {
                  runIdRef.current = data.run_id;
                  handlers.onRunId?.(data.run_id);
                }
              } catch {
                /* ignore malformed */
              }
              eventName = "message";
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          handlers.onError("network_error", (err as Error).message);
        }
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [],
  );

  return { stream, stop, streaming };
}
