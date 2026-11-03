export type User = {
  id: string;
  email: string;
  daily_request_quota: number;
  daily_token_quota: number;
  created_at: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type Thread = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  thread_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
};

export type UsageInfo = {
  input_tokens: number;
  output_tokens: number;
  tier: string;
  provider: string;
  model: string;
  estimated_commercial_cost_usd: number;
};

export type StreamDone = {
  message_id: string;
  run_id?: string;
  usage: UsageInfo;
};
