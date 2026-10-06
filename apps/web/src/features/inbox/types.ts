export interface EmailMessage {
  id: string;
  gmail_message_id: string;
  gmail_thread_id: string;
  sender: string;
  recipient: string;
  subject: string;
  snippet: string;
  body_text: string;
  received_at: string;
  is_unread: boolean;
  labels: string[];
  category: "work" | "finance" | "personal" | "newsletters" | "promotions" | "alerts" | "other" | string;
  importance: number;
  needs_reply: boolean;
  summary: string | null;
  suggested_action: string | null;
  triaged_at: string | null;
}

export interface Draft {
  id: string;
  user_id: string;
  mailbox_id: string;
  email_id: string | null;
  gmail_thread_id: string | null;
  to_email: string;
  subject: string;
  body: string;
  tone: string;
  status: "DRAFTED" | "APPROVED" | "SENDING" | "SENT";
  approved_content_sha256: string | null;
  approved_at: string | null;
  send_idempotency_key: string | null;
  sent_at: string | null;
  gmail_message_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SyncResult {
  mailbox_id: string;
  gmail_address: string;
  synced_count: number;
  new_messages: number;
  triaged_count: number;
  duration_ms: number;
}
