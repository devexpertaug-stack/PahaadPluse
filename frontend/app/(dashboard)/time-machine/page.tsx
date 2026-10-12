"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, Card, Badge } from "@/components/ui";
import { LineChart, type Series } from "@/components/charts/LineChart";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import {
  api,
  type DecompositionResponse,
  type ReviewCountsResponse,
  type TimeMachineResponse,
} from "@/lib/api";
import { palette } from "@/lib/theme";

const FOCUS_ASPECT = "Food";

const scopeTone: Record<string, "forest" | "dawn" | "neutral"> = {
  "property-specific": "forest",
  "market-wide": "dawn",
  undetermined: "neutral",
};

export default function TimeMachinePage() {
  // The home property and its decomposition series are both live. The chart
  // drives which month we investigate on the Time Machine endpoint.
  const counts = useLiveData<ReviewCountsResponse>(() => api.reviewCounts());
  const decompState = useLiveData<DecompositionResponse>(() =>
    api.decomposition(),
  );

  const homeId = counts.data?.properties[0]?.property_id ?? "";
  const homeName = counts.data?.properties[0]?.property_name ?? "the home property";

  const cells = useMemo(() => {
    const all = decompState.data?.cells ?? [];
    return all
      .filter((c) => c.property_id === homeId && c.aspect === FOCUS_ASPECT)
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [decompState.data, homeId]);

  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<TimeMachineResponse | null>(null);
  const [investigating, setInvestigating] = useState(false);
  const [tmError, setTmError] = useState(false);

  function investigate(month: string) {
    if (!homeId) return;
    setSelected(month);
    setInvestigating(true);
    setTmError(false);
    api
      .timeMachine(homeId, month, FOCUS_ASPECT)
      .then((r) => setResult(r))
      .catch(() => setTmError(true))
      .finally(() => setInvestigating(false));
  }

  // Auto-investigate the first available month once the live series loads.
  useEffect(() => {
    if (cells.length > 0 && selected === null) {
      investigate(cells[0].month);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells]);

  const labels = cells.map((c) => c.month);
  const series: Series[] = [
    {
      label: `${FOCUS_ASPECT} score`,
      color: palette.forest.bright,
      points: cells.map((c) => c.modelled_score),
    },
  ];

  const badge = liveBadgeProps(decompState.status);
  const cp = result?.changepoint ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F2"
        title="Root-Cause Time Machine"
        description={`Click a point on ${homeName}'s ${FOCUS_ASPECT} series to jump to the nearest changepoint and mine what guests said before and after.`}
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <LoadState
        status={decompState.status}
        onRetry={decompState.reload}
        emptyBody="The decomposition model returned no cells for the home property yet. Seed or ingest reviews to populate the Time Machine."
      >
        <Card
          title={`${homeName} · ${FOCUS_ASPECT} score`}
          subtitle="Select a month to investigate (within ±30 days of a changepoint)"
          className="mb-6"
        >
          <LineChart
            labels={labels}
            series={series}
            yMin={1}
            yMax={5}
            yLabel="score"
            ariaLabel="time machine series"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {cells.map((c) => (
              <button
                key={c.month}
                type="button"
                onClick={() => investigate(c.month)}
                className={`rounded-md border px-2 py-1 text-xs ${
                  selected === c.month
                    ? "border-forest-600 bg-forest-100 text-forest-800"
                    : "border-mist-300 bg-mist-50 text-forest-600 hover:bg-mist-100"
                }`}
              >
                {c.month.slice(0, 7)}
              </button>
            ))}
          </div>
        </Card>

        {tmError ? (
          <Card title="Investigation unavailable">
            <p className="text-sm text-forest-600">
              Could not reach the Time Machine endpoint. This view shows live
              data only — reload once the backend is reachable.
            </p>
          </Card>
        ) : investigating && !result ? (
          <Card>
            <p className="text-sm text-forest-600">Investigating…</p>
          </Card>
        ) : result && cp ? (
          <>
            <div className="mb-6 grid gap-5 lg:grid-cols-3">
              <Card title="Nearest changepoint" subtitle={`series: ${cp.series}`}>
                <p className="text-sm text-forest-700">
                  <span className="font-semibold">{cp.date}</span> ·{" "}
                  <span
                    className={
                      cp.direction === "decline"
                        ? "text-dawn-600"
                        : "text-forest-700"
                    }
                  >
                    {cp.direction}
                  </span>
                </p>
                <p className="mt-1 text-sm text-forest-600">
                  Posterior {cp.posterior.toFixed(2)}
                  {cp.unreliable && " · flagged unreliable"}
                </p>
                <div className="mt-2">
                  <Badge tone={scopeTone[result.scope_label] ?? "neutral"}>
                    {result.scope_label}
                  </Badge>
                </div>
              </Card>

              <Card
                title="Candidate causes"
                subtitle="Ranked by lift (after-share / before-share)"
                className="lg:col-span-2"
              >
                {result.causes.length === 0 ? (
                  <p className="text-sm text-forest-600">
                    {result.message ?? "No qualifying cause phrases."}
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {result.causes.map((c) => (
                      <li
                        key={c.phrase}
                        className="flex items-center justify-between rounded-lg bg-mist-100 px-3 py-2 text-sm"
                      >
                        <span className="font-medium text-forest-800">
                          “{c.phrase}”
                        </span>
                        <span className="tabular-nums text-forest-600">
                          lift {c.lift.toFixed(2)} · after {c.after_count} /
                          before {c.before_count}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            {result.limited_evidence && (
              <div className="mb-4">
                <Badge tone="dawn">limited evidence (fewer than 2 quotes)</Badge>
              </div>
            )}

            <div className="mb-6 grid gap-5 lg:grid-cols-2">
              <QuoteList
                title="Before the changepoint"
                quotes={result.before_quotes}
              />
              <QuoteList
                title="After the changepoint"
                quotes={result.after_quotes}
              />
            </div>

            <Card
              title="Logged interventions & events"
              subtitle="Operational changes within ±30 days"
            >
              {result.interventions.length === 0 ? (
                <p className="text-sm text-forest-600">
                  No interventions logged near this changepoint.
                </p>
              ) : (
                <ul className="list-disc space-y-1 pl-5 text-sm text-forest-700">
                  {result.interventions.map((i) => (
                    <li key={`${i.date}-${i.label}`}>
                      <span className="font-medium">{i.date}</span> — {i.label}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </>
        ) : result ? (
          <Card title="No changepoint">
            <p className="text-sm text-forest-600">
              {result.message ??
                "No changepoint within 30 days of the selected point."}
            </p>
          </Card>
        ) : null}
      </LoadState>
    </div>
  );
}

function QuoteList({
  title,
  quotes,
}: {
  title: string;
  quotes: TimeMachineResponse["before_quotes"];
}) {
  return (
    <Card title={title} subtitle={`${quotes.length} aspect-matched quotes`}>
      {quotes.length === 0 ? (
        <p className="text-sm text-forest-600">No quotes in this window.</p>
      ) : (
        <ul className="space-y-3">
          {quotes.map((q, i) => (
            <li key={i} className="rounded-lg bg-mist-100 px-3 py-2 text-sm">
              <p className="text-forest-800">“{q.span}”</p>
              <p className="mt-1 text-xs text-forest-500">
                {q.platform} · {q.date}
                {q.source_url ? (
                  <>
                    {" · "}
                    <a
                      href={q.source_url}
                      className="text-forest-600 underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      source
                    </a>
                  </>
                ) : (
                  " · source URL unavailable"
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
