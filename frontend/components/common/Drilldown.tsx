"use client";

/**
 * F14 Every-number-is-clickable Drilldown (Req 27).
 *
 * A reusable overlay that turns any displayed count / share / score / chart
 * point into a button. Clicking it fetches the exact source Review_Records (or
 * Complaints) behind the number, highlights each relevant Aspect_Mention
 * evidence span and shows each record's source URL (or "source URL
 * unavailable"). For a count metric the overlay asserts the trust invariant:
 * the number of listed records equals the clicked count.
 */

import { useCallback, useState } from "react";
import { api, type DrilldownQuery, type DrilldownResponse } from "@/lib/api";

export interface DrilldownProps extends DrilldownQuery {
  /** The rendered number / label the user clicks. */
  children: React.ReactNode;
  className?: string;
  /** Optional bundled fallback used when the API is offline (tests/demo). */
  fallback?: DrilldownResponse;
}

function Highlight({
  text,
  start,
  end,
}: {
  text: string;
  start: number;
  end: number;
}) {
  if (start < 0 || end <= start || end > text.length) {
    return <span>{text}</span>;
  }
  return (
    <span>
      {text.slice(0, start)}
      <mark className="rounded bg-dawn-400/40 px-0.5 text-forest-900">
        {text.slice(start, end)}
      </mark>
      {text.slice(end)}
    </span>
  );
}

export function Drilldown({
  children,
  className,
  fallback,
  ...query
}: DrilldownProps) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<DrilldownResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.drilldown(query);
      setData(res);
    } catch {
      setData(fallback ?? null);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fallback, JSON.stringify(query)]);

  function openPanel() {
    setOpen(true);
    void load();
  }

  return (
    <>
      <button
        type="button"
        onClick={openPanel}
        title="Drill down to the source records"
        className={
          className ??
          "cursor-pointer rounded underline decoration-dotted decoration-pine-400 underline-offset-2 hover:text-pine-600"
        }
      >
        {children}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-forest-900/40 p-4 sm:p-8"
          role="dialog"
          aria-modal="true"
          onClick={() => setOpen(false)}
        >
          <div
            className="mt-6 w-full max-w-2xl rounded-2xl border border-mist-300 bg-mist-50 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-start justify-between gap-4 border-b border-mist-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-pine-500">
                  Drilldown · source records
                </p>
                <h3 className="mt-1 text-base font-semibold text-forest-800">
                  {query.metric}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg px-2 py-1 text-forest-600 hover:bg-mist-200"
                aria-label="Close drilldown"
              >
                ✕
              </button>
            </header>

            <div className="px-5 py-4">
              {loading && (
                <p className="text-sm text-forest-600">Loading source records…</p>
              )}
              {!loading && !data && (
                <p className="text-sm text-forest-600">
                  No source records available.
                </p>
              )}
              {!loading && data && (
                <>
                  <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
                    <span className="rounded-full bg-forest-100 px-3 py-1 font-medium text-forest-800">
                      {data.count} source record{data.count === 1 ? "" : "s"}
                    </span>
                    {data.is_count && (
                      <span
                        className={
                          data.count_matches
                            ? "rounded-full bg-forest-100 px-3 py-1 text-forest-700"
                            : "rounded-full bg-dawn-400/30 px-3 py-1 text-forest-800"
                        }
                      >
                        {data.count_matches
                          ? `matches clicked value (${data.clicked_value})`
                          : `clicked ${data.clicked_value}`}
                      </span>
                    )}
                  </div>

                  <ul className="space-y-3">
                    {data.records.map((rec, i) => (
                      <li
                        key={`${rec.property_id}-${rec.date}-${i}`}
                        className="rounded-xl border border-mist-200 bg-mist-100 p-3"
                      >
                        <div className="flex flex-wrap items-center gap-2 text-xs text-forest-600">
                          <span className="font-medium text-forest-800">
                            {rec.property_name}
                          </span>
                          {rec.platform && <span>· {rec.platform}</span>}
                          {rec.aspect && <span>· {rec.aspect}</span>}
                          {rec.label && <span>· {rec.label}</span>}
                          <span>· {rec.date}</span>
                        </div>
                        <p className="mt-2 text-sm text-forest-800">
                          “
                          <Highlight
                            text={rec.evidence.text}
                            start={rec.evidence.start}
                            end={rec.evidence.end}
                          />
                          ”
                        </p>
                        <p className="mt-2 text-xs">
                          {rec.source_url_available ? (
                            <a
                              href={rec.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-pine-600 underline"
                            >
                              {rec.source_url}
                            </a>
                          ) : (
                            <span className="text-forest-500/70">
                              {rec.source_url}
                            </span>
                          )}
                        </p>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
