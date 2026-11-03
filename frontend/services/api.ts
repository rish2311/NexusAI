import type { ChatMessage, Thread, TokenPair, User } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_KEY = "nexusai_access_token";
const REFRESH_KEY = "nexusai_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  const res = await fetch(`${API_URL}/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = (await res.json()) as TokenPair;
  setTokens(data);
  return data.access_token;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiFetch<T>(path, options, false);
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail =
        typeof err.detail === "string"
          ? err.detail
          : err.detail?.message || JSON.stringify(err.detail) || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const authApi = {
  register: (email: string, password: string) =>
    apiFetch<TokenPair>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    apiFetch<TokenPair>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => apiFetch<User>("/v1/auth/me"),
  logout: async () => {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        await apiFetch("/v1/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refresh }),
        });
      } catch {
        /* ignore */
      }
    }
    clearTokens();
  },
};

export const threadsApi = {
  list: () => apiFetch<Thread[]>("/v1/threads"),
  create: (title = "New chat") =>
    apiFetch<Thread>("/v1/threads", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  get: (id: string) => apiFetch<Thread>(`/v1/threads/${id}`),
  rename: (id: string, title: string) =>
    apiFetch<Thread>(`/v1/threads/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  remove: (id: string) =>
    apiFetch<void>(`/v1/threads/${id}`, { method: "DELETE" }),
  messages: (id: string) =>
    apiFetch<{ items: ChatMessage[]; next_cursor: string | null }>(
      `/v1/threads/${id}/messages`,
    ),
};

export function getApiUrl(): string {
  return API_URL;
}
