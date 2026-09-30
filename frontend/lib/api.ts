// Thin API client. Talks to the FastAPI backend via the Next.js /api rewrite.

const BASE = "/api";

export function getToken(): string | null {
  try { return localStorage.getItem("token"); } catch { return null; }
}
export function setToken(t: string | null) {
  try { t ? localStorage.setItem("token", t) : localStorage.removeItem("token"); } catch {}
}

type Opts = { method?: string; body?: any; auth?: boolean; form?: FormData };

export async function api<T = any>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (opts.auth !== false && token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form; // browser sets multipart boundary
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(`${BASE}${path}`, { method: opts.method || "GET", headers, body });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text() as unknown as T;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export const fileUrl = (docId: number) => `${BASE}/documents/${docId}/file`;

/**
 * Download a protected file (CSV/PDF/etc.). A plain <a href> can't send the JWT,
 * so we fetch with the auth header, then trigger a save from the returned blob.
 */
export async function apiDownload(path: string, filename: string): Promise<void> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { headers });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new ApiError(typeof detail === "string" ? detail : "Download failed", res.status);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Fetch a protected file with auth and return a blob object URL — for viewing in
 * an <iframe> or a new tab (which also can't send the JWT header on their own).
 * The caller is responsible for URL.revokeObjectURL() when done.
 */
export async function apiObjectUrl(path: string): Promise<string> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { headers });
  if (!res.ok) throw new ApiError("Could not load file", res.status);
  return URL.createObjectURL(await res.blob());
}
