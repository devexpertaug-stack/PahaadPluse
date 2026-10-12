"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, Card, Badge } from "@/components/ui";
import { LineChart, type Series } from "@/components/charts/LineChart";
import {
  api,
  type ChangepointsResponse,
  type DecompositionResponse,
  type TimeMachineResponse,
} from "@/lib/api";
import analytics from "@/lib/analyticsSnapshot.json";
import { palette } from "@/lib/theme";

const CHANGEPOINTS = analytics.changepoints as unknown as ChangepointsResponse;
const DECOMP = analytics.decomposition as unknown as DecompositionResponse;
const TIME_MACHINE = analytics.timeMachine as unknown as TimeMachineResponse;
const HOME = analytics.homeProperty as { id: string; name: string };
const FOCUS_ASPECT = "Food";

const scopeTone: Record<string, "forest" | "dawn" | "neutral"> = {
  "property-specific": "forest",
  "market-wide": "dawn",
  undetermined: "neutral",
};

export default function TimeMachinePage() {
  const [result, setResult] = useState<TimeMachineResponse>(TIME_MACHINE);
  const [live, setLive] = useState(false);
  const [selected, setSelected] = useState<string>("2024-01-01");

  const cells = useMemo(
    () =>
      DECOMP.cells
        .filter(
          (c) => c.property_id === HOME.id && c.aspect === FOCUS_ASPECT,
        )
        .sort((a, b) => a.month.localeCompare(b.month)),
    [],
  );

  const labels = cells.map((c) => c.month);
  const series: Series[] = [
    {
      label: `${FOCUS_ASPECT} score`,
      color: palette.forest.bright,
      points: cells.map((c) => c.modelled_score),
    },
  ];

  function investigate(month: string) {
    setSelected(month);
    api
      .timeMachine(HOME.id, month, FOCUS_ASPECT)
      .then((r) => {
        setResult(r);
        setLive(true);
      })
      .catch(() => {
        /* keep snapshot */
      });
  }

  useEffect(() => {
    investigate(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cp = result.changepoint;

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F2"
        title="Root-Cause Time Machine"
        description={`Click a point on ${HOME.name}'s ${FOCUS_ASPECT} series to jump to the nearest changepoint and mine what guests said before and after.`}
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

      <Card
        title={`${HOME.name} · ${FOCUS_ASPECT} score`}
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

      {cp ? (
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
                        lift {c.lift.toFixed(2)} · after {c.after_count} / before{" "}
                        {c.before_count}
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
            <QuoteList title="Before the changepoint" quotes={result.before_quotes} />
            <QuoteList title="After the changepoint" quotes={result.after_quotes} />
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
      ) : (
        <Card title="No changepoint">
          <p className="text-sm text-forest-600">
            {result.message ?? "No changepoint within 30 days of the selected point."}
          </p>
        </Card>
      )}
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
