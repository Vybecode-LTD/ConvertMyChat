import type {
  ExtractResponse, ExportRequest, ConversationData, ExportFormat,
  AuthResponse, UserData, HistoryItem, AdminStats,
  ExtractResponseV2, BundleExportRequest, ShareResponse,
} from "@/types";

const API = import.meta.env.VITE_API_URL || "";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("cmc_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...opts.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// === Extract/Export (public) ===
export const extractConversation = (url: string) =>
  api<ExtractResponse>("/api/extract", { method: "POST", body: JSON.stringify({ url }) });

export const extractConversationV2 = (url: string) =>
  api<ExtractResponseV2>("/api/extract-v2", { method: "POST", body: JSON.stringify({ url }) });

export async function exportBundle(
  convo: ConversationData, format: ExportFormat,
  include_tables = true, include_json = true, include_code = true,
) {
  const body: BundleExportRequest = {
    conversation: convo, format, include_tables, include_json, include_code,
  };
  const res = await fetch(`${API}/api/export-bundle`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Bundle export failed" }));
    throw new Error(err.detail || `HTTP ${res.status}: bundle export failed`);
  }
  return { blob: await res.blob(), filename: res.headers.get("X-Filename") || "export_bundle.zip" };
}

export async function exportConversation(convo: ConversationData, format: ExportFormat) {
  const res = await fetch(`${API}/api/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ conversation: convo, format }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(err.detail || "Export failed");
  }
  const ext = format === "markdown" ? "md" : format;
  return { blob: await res.blob(), filename: res.headers.get("X-Filename") || `export.${ext}` };
}

// === Share ===
export const createShare = (convo: ConversationData) =>
  api<ShareResponse>("/api/share", { method: "POST", body: JSON.stringify({ conversation: convo }) });

export function downloadBlob(blob: Blob, filename: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

// === Auth ===
export const register = (email: string, password: string, display_name?: string) =>
  api<AuthResponse>("/api/auth/register", {
    method: "POST", body: JSON.stringify({ email, password, display_name }),
  });

export const login = (email: string, password: string) =>
  api<AuthResponse>("/api/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  });

export const getMe = () => api<UserData>("/api/auth/me");

// === History ===
export const getHistory = (skip = 0, limit = 20) =>
  api<{ items: HistoryItem[]; total: number }>(`/api/history/?skip=${skip}&limit=${limit}`);

export const deleteHistoryItem = (id: string) =>
  api<{ deleted: boolean }>(`/api/history/${id}`, { method: "DELETE" });

export async function reexportHistoryItem(id: string, format: ExportFormat) {
  const res = await fetch(`${API}/api/history/${id}/reexport?format=${format}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Re-export failed");
  const ext = format === "markdown" ? "md" : format;
  return { blob: await res.blob(), filename: `reexport.${ext}` };
}

// === Admin ===
export const adminListUsers = (skip = 0, limit = 50, search?: string) => {
  let url = `/api/admin/users?skip=${skip}&limit=${limit}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  return api<{ users: UserData[]; total: number }>(url);
};

export const adminCreateUser = (data: { email: string; password: string; display_name?: string; is_admin?: boolean }) =>
  api<UserData>("/api/admin/users", { method: "POST", body: JSON.stringify(data) });

export const adminUpdateUser = (id: string, data: { display_name?: string; is_active?: boolean; is_admin?: boolean }) =>
  api<UserData>(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const adminResetPassword = (id: string, new_password: string) =>
  api<{ success: boolean }>(`/api/admin/users/${id}/reset-password`, {
    method: "POST", body: JSON.stringify({ new_password }),
  });

export const adminDeleteUser = (id: string) =>
  api<{ deleted: boolean }>(`/api/admin/users/${id}`, { method: "DELETE" });

export const adminStats = () => api<AdminStats>("/api/admin/stats");
