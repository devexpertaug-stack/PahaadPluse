"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

/**
 * Client-side session gate for the dashboard. On mount it checks for a stored
 * session token; if none exists it redirects to `/login`. While the check runs
 * (and on the server, where `localStorage` is unavailable) it renders nothing
 * so there is no hard crash on first paint. Demo-grade: the token is not
 * re-validated against the backend here, it simply gates the UI on the presence
 * of a stored token. If the token is actually expired, the first authenticated
 * API call returns `401`, and `lib/api.ts` then clears the session and
 * redirects back to `/login` (so an expired session bounces to login rather
 * than lingering on error panels).
 */
export function SessionGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return null;
  }
  return <>{children}</>;
}
