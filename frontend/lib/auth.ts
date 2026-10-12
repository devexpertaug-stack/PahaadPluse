/**
 * Lightweight client-side session store for the PahadPulse demo login.
 *
 * The signed session token issued by `POST /auth/login` is persisted in
 * `localStorage` (demo-grade) and read back by `lib/api.ts` to attach an
 * `Authorization: Bearer` header, and by the dashboard layout to gate access.
 * Everything is guarded for SSR (no `window` on the server) so it never
 * hard-crashes on first paint.
 */

export interface SessionUser {
  id: string;
  username: string;
  display_name: string;
  role: string;
  property_id: string;
  property_name: string;
}

const TOKEN_KEY = "pahadpulse.token";
const USER_KEY = "pahadpulse.user";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

export function getToken(): string | null {
  if (!hasWindow()) return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getUser(): SessionUser | null {
  if (!hasWindow()) return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as SessionUser) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: SessionUser): void {
  if (!hasWindow()) return;
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* ignore storage failures (private mode, quota) */
  }
}

export function clearSession(): void {
  if (!hasWindow()) return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}
