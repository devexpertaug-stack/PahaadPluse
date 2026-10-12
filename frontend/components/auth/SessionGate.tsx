"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

/**
 * Client-side session gate for the dashboard. On mount it checks for a stored
 * session token; if none exists it redirects to `/login`. While the check runs
 * (and on the server, where `localStorage` is unavailable) it renders nothing
 * so there is no hard crash on first paint. Demo-grade: the token is not
 * re-validated against the backend here (the API calls themselves 401 on an
 * expired token), it simply gates the UI.
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
