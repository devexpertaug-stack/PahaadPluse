/**
 * Typed fetch client for the PahadPulse FastAPI backend.
 *
 * The base URL comes from `NEXT_PUBLIC_API_BASE_URL` (set by `make demo`) and
 * defaults to the local API port.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed with ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
};
