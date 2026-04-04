import { apiUrl } from "@/shared/api/client";

export class ApiError extends Error {
  readonly status: number;
  readonly bodyText: string;
  readonly detail: unknown;

  constructor(status: number, bodyText: string, detail: unknown) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.bodyText = bodyText;
    this.detail = detail;
  }
}

function parseDetail(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export function formatApiError(err: unknown): string {
  if (err instanceof ApiError) {
    const d = err.detail;
    if (typeof d === "string") return d;
    if (d && typeof d === "object") {
      const rec = d as Record<string, unknown>;
      if (typeof rec.detail === "string") return rec.detail;
      if (Array.isArray(rec.detail)) return JSON.stringify(rec.detail, null, 2);
      if (rec.detail && typeof rec.detail === "object") {
        return JSON.stringify(rec.detail, null, 2);
      }
      if (Array.isArray(rec.errors)) return JSON.stringify(rec.errors, null, 2);
    }
    return err.bodyText || err.message;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}

export async function apiJson<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const headers = new Headers(init?.headers);
  let body = init?.body;
  if (init?.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(apiUrl(path), { ...init, headers, body });
  const text = await res.text();
  if (!res.ok) {
    throw new ApiError(res.status, text, parseDetail(text));
  }
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

/** Скачивание бинарного файла (DOCX и т.п.). */
export async function apiBlob(path: string): Promise<Blob> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text, parseDetail(text));
  }
  return res.blob();
}
