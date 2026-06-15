export type ExportFormat = "pdf" | "docx" | "csv" | "markdown" | "html";
export type AppStatus = "idle" | "validating" | "extracting" | "extracted" | "exporting" | "done" | "error";
export type AppView = "home" | "history" | "admin";

export interface ConversationMessage {
  role: "user" | "model";
  content: string;
  index: number;
  has_code_blocks: boolean;
  code_blocks: Array<{ language: string; code: string }>;
}

export interface ConversationData {
  title: string;
  share_url: string;
  extracted_at: string;
  message_count: number;
  messages: ConversationMessage[];
  metadata: Record<string, unknown>;
}

export interface ExtractResponse {
  success: boolean;
  conversation: ConversationData | null;
  error: string | null;
  cached: boolean;
}

export interface EmbeddedContentItem {
  content_type: "table" | "json" | "code";
  suggested_filename: string;
  language: string | null;
  row_count: number | null;
  column_count: number | null;
  message_index: number;
  message_role: string;
  preview: string;
}

export interface ContentSummary {
  tables: number;
  json: number;
  code: number;
  total: number;
}

export interface ExtractResponseV2 {
  success: boolean;
  conversation: ConversationData | null;
  embedded_content: EmbeddedContentItem[];
  content_summary: ContentSummary;
  error: string | null;
  cached: boolean;
}

export interface BundleExportRequest {
  conversation: ConversationData;
  format: ExportFormat;
  include_tables: boolean;
  include_json: boolean;
  include_code: boolean;
}

export interface ExportRequest {
  conversation: ConversationData;
  format: ExportFormat;
}

export interface UserData {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  auth_provider: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserData;
}

export interface HistoryItem {
  id: string;
  share_url: string;
  title: string;
  message_count: number;
  last_export_format: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_exports: number;
  cached_conversations: number;
}

export interface ShareResponse {
  id: string;
  share_url: string;
  title: string;
  message_count: number;
  created_at: string;
  view_url: string;
}

export const FORMAT_LABELS: Record<ExportFormat, string> = {
  pdf: "PDF", docx: "Word (DOCX)", csv: "CSV", markdown: "Markdown", html: "HTML",
};
export const FORMAT_ICONS: Record<ExportFormat, string> = {
  pdf: "📄", docx: "📝", csv: "📊", markdown: "📋", html: "🌐",
};
