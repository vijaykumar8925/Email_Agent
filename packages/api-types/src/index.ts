/**
 * Core Mail Agent API Types
 * Mirrors backend OpenAPI schema definitions.
 */

export type EmailCategory =
  | "work"
  | "finance"
  | "personal"
  | "newsletters"
  | "promotions"
  | "alerts"
  | "other";

export type MailboxStatus = "active" | "needs_reauth" | "disconnected";

export type DraftStatus = "drafted" | "approved" | "sending" | "sent" | "failed" | "rejected";

export type AuditActor = "user" | "system" | "ai";

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface MailboxResponse {
  id: string;
  user_id: string;
  provider: "gmail";
  provider_account_email: string;
  status: MailboxStatus;
  history_id: string | null;
  watch_expiration: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailAnalysisResponse {
  id: string;
  email_id: string;
  category: EmailCategory;
  importance: number;
  needs_reply: boolean;
  summary: string;
  reasoning_short: string;
  model: string;
  prompt_version: string;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
}

export interface EmailResponse {
  id: string;
  mailbox_id: string;
  provider_message_id: string;
  thread_id: string;
  from_name: string | null;
  from_address: string;
  to_addresses: string[];
  cc_addresses: string[];
  subject: string;
  snippet: string | null;
  received_at: string;
  is_unread: boolean;
  labels: string[];
  body_text?: string | null;
  analysis?: EmailAnalysisResponse | null;
}

export interface DraftResponse {
  id: string;
  email_id: string;
  user_id: string;
  template_id: string | null;
  subject: string;
  body: string;
  status: DraftStatus;
  approved_by_user_id: string | null;
  approved_at: string | null;
  approved_content_sha256: string | null;
  failure_reason: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateResponse {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  body: string;
  tone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export interface ReadyResponse {
  status: string;
  components: {
    database: string;
    redis: string;
  };
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: string;
  request_id?: string;
}
