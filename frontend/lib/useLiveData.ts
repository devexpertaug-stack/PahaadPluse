"use client";

/**
 * Shared live-data load-state hook for the PahadPulse dashboard.
 *
 * The dashboard is a LIVE demo: the seeded/ingested Forest Season Resort data
 * from the FastAPI backend is the single source of truth. Pages must never
 * silently paper over a working-but-empty or unreachable backend with a baked
 * snapshot. This hook models four honest states so every page can render a
 * tidy loading / empty / error UI:
 *
 *   - "loading" — first paint, request in flight
 *   - "ready"   — live data arrived and is non-empty
 *   - "empty"   — live data arrived but the backend returned nothing to show
 *   - "error"   — the backend could not be reached / returned a failure
 *
 * `isEmpty` lets each page decide what "nothing to show" means for its shape.
 */

import { useCallback, useEffect, useState } from "react";

export type LoadStatus = "loading" | "ready" | "empty" | "error";

export interface LiveData<T> {
  status: LoadStatus;
  data: T | null;
  error: string | null;
  /** Re-run the fetcher (e.g. after a mutation or filter change). */
  reload: () => void;
}

export interface UseLiveDataOptions<T> {
  /** Returns true when the live payload has nothing meaningful to render. */
  isEmpty?: (data: T) => boolean;
  /** Re-fetch whenever one of these values changes. */
  deps?: ReadonlyArray<unknown>;
}

export function useLiveData<T>(
  fetcher: () => Promise<T>,
  options: UseLiveDataOptions<T> = {},
): LiveData<T> {
  const { isEmpty, deps = [] } = options;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    setError(null);
    fetcher()
      .then((result) => {
        if (!active) return;
        setData(result);
        setStatus(isEmpty && isEmpty(result) ? "empty" : "ready");
      })
      .catch((err: unknown) => {
        if (!active) return;
        setData(null);
        setError(err instanceof Error ? err.message : "Request failed");
        setStatus("error");
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);

  return { status, data, error, reload };
}
