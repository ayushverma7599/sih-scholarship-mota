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
