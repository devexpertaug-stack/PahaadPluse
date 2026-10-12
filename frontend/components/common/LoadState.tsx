"use client";

import type { ReactNode } from "react";
import { Button, Card } from "@/components/ui";
import type { LoadStatus } from "@/lib/useLiveData";

/**
 * Presentational wrapper for the live-data load states (see lib/useLiveData).
 *
 * It renders tidy, intentional-looking loading / empty / error panels built
 * from the shared UI primitives so an unreachable or empty backend never looks
 * broken during a live demo — and never silently falls back to stale data.
 */
export interface LoadStateProps {
  status: LoadStatus;
  /** Shown while loading. Defaults to a generic skeleton message. */
  loadingLabel?: string;
  /** Title/body for the empty state. */
  emptyTitle?: string;
  emptyBody?: ReactNode;
  /** Title/body for the error state. */
  errorTitle?: string;
  errorBody?: ReactNode;
  /** Optional retry handler, surfaced on the error state. */
  onRetry?: () => void;
  /** Rendered only when status === "ready". */
  children: ReactNode;
}

export function LoadState({
  status,
  loadingLabel = "Loading live data from the backend…",
  emptyTitle = "Nothing to show yet",
  emptyBody = "The backend is reachable but has not returned any data for this view. Seed or ingest reviews to populate it.",
  errorTitle = "Backend unavailable",
  errorBody = "Could not reach the PahadPulse API. Start the backend (make demo) and reload — this view shows live data only, never a stale snapshot.",
  onRetry,
  children,
}: LoadStateProps) {
  if (status === "loading") {
    return <LoadingPanel label={loadingLabel} />;
  }
  if (status === "empty") {
    return (
      <Card title={emptyTitle}>
        <p className="text-sm text-forest-600">{emptyBody}</p>
      </Card>
    );
  }
  if (status === "error") {
    return (
      <Card title={errorTitle}>
        <p className="text-sm text-forest-600">{errorBody}</p>
        {onRetry && (
          <div className="mt-3">
            <Button variant="secondary" size="sm" onClick={onRetry}>
              Retry
            </Button>
          </div>
        )}
      </Card>
    );
  }
  return <>{children}</>;
}

function LoadingPanel({ label }: { label: string }) {
  return (
    <Card>
      <div className="flex items-center gap-3 py-4">
        <span
          aria-hidden
          className="h-4 w-4 animate-spin rounded-full border-2 border-forest-300 border-t-forest-600"
        />
        <p className="text-sm text-forest-600">{label}</p>
      </div>
      <div className="mt-2 space-y-2" aria-hidden>
        <div className="h-3 w-3/4 animate-pulse rounded bg-mist-200" />
        <div className="h-3 w-1/2 animate-pulse rounded bg-mist-200" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-mist-200" />
      </div>
    </Card>
  );
}

/** Small inline status badge helper for the "Live from API" header pill. */
export function liveBadgeProps(status: LoadStatus): {
  tone: "forest" | "dawn" | "slate";
  label: string;
} {
  switch (status) {
    case "ready":
      return { tone: "forest", label: "Live from API" };
    case "empty":
      return { tone: "slate", label: "Live · no data" };
    case "error":
      return { tone: "dawn", label: "Backend unavailable" };
    default:
      return { tone: "slate", label: "Loading…" };
  }
}
