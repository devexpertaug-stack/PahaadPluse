"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import {
  api,
  ASPECTS,
  PLATFORMS,
  type WhatIfModel,
  type WhatIfProjection,
} from "@/lib/api";
import snapshot from "@/lib/analyticsSnapshot.json";

const SNAP = snapshot.whatIf as Record<string, WhatIfModel>;

function localProjection(
  model: WhatIfModel,
  deltas: Record<string, number>,
): WhatIfProjection {
  // Mirror the backend projection so the page works offline (snapshot mode).
  const weightByAspect = new Map(model.driver_weights.map((d) => [d.aspect, d]));
  let total = 0;
  let lo = 0;
  let hi = 0;
  const applied: { aspect: string; delta: number }[] = [];
  for (const [aspect, raw] of Object.entries(deltas)) {
    const dw = weightByAspect.get(aspect);
    if (!dw || !dw.available || raw === 0) continue;
    total += dw.weight * raw;
    lo += dw.lower * raw;
    hi += dw.upper * raw;
    applied.push({ aspect, delta: raw });
  }
  const bound = (v: number) => Math.max(1, Math.min(5, v));
  const projected = bound(model.current_rating + total);
  return {
    platform: model.platform,
    current_rating: Number(model.current_rating.toFixed(2)),
    projected_rating: Number(projected.toFixed(2)),
    projected_lower: Number(bound(model.current_rating + Math.min(lo, hi)).toFixed(2)),
    projected_upper: Number(bound(model.current_rating + Math.max(lo, hi)).toFixed(2)),
    projected_rank: 0,
    cluster_size: model.cluster_size,
    low_confidence: model.low_confidence,
    applied_deltas: applied,
  };
}

export default function WhatIfPage() {
  const [platform, setPlatform] = useState<string>(PLATFORMS[0]);
  const [model, setModel] = useState<WhatIfModel>(SNAP[PLATFORMS[0]]);
  const [deltas, setDeltas] = useState<Record<string, number>>({});
  const [projection, setProjection] = useState<WhatIfProjection | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setModel(SNAP[platform]);
    setDeltas({});
    setProjection(null);
    api
      .whatIfModel(platform)
      .then((m) => {
        if (active) {
          setModel(m);
          setLive(true);
        }
      })
      .catch(() => {
        /* keep snapshot */
      });
    return () => {
      active = false;
    };
  }, [platform]);

  const rankedWeights = useMemo(
    () =>
      [...model.driver_weights].sort(
        (a, b) => Math.abs(b.weight) - Math.abs(a.weight),
      ),
    [model],
  );

  function runProjection(next: Record<string, number>) {
    setError(null);
    if (live) {
      api
        .whatIfProject(platform, next)
        .then(setProjection)
        .catch(() => {
          setError("Projection failed; showing the previous result.");
        });
    } else {
      setProjection(localProjection(model, next));
    }
  }

  function onSlider(aspect: string, value: number) {
    const next = { ...deltas, [aspect]: value };
    setDeltas(next);
    runProjection(next);
  }

  const noData = model.driver_weights.every((d) => !d.available);

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F1"
        title="Rating What-If Simulator"
        description="Model the projected overall rating and cluster rank before you make a change. Driver weights come from all cluster reviews on the selected platform."
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        {PLATFORMS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPlatform(p)}
            className={`rounded-full border px-3 py-1 text-sm font-medium ${
              platform === p
                ? "border-forest-600 bg-forest-100 text-forest-800"
                : "border-mist-300 bg-mist-50 text-forest-600 hover:bg-mist-100"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Current rating"
          value={model.current_rating.toFixed(2)}
          hint={`on ${platform}`}
        />
        <StatTile
          label="Projected rating"
          value={projection ? projection.projected_rating.toFixed(2) : "—"}
          trend={
            projection
              ? projection.projected_rating > model.current_rating
                ? "up"
                : projection.projected_rating < model.current_rating
                  ? "down"
                  : "flat"
              : "flat"
          }
          hint={
            projection
              ? `90% CI ${projection.projected_lower.toFixed(2)}–${projection.projected_upper.toFixed(2)}`
              : "adjust a slider"
          }
        />
        <StatTile
          label="Projected cluster rank"
          value={projection && projection.projected_rank ? `#${projection.projected_rank}` : "—"}
          hint={`of ${model.cluster_size}`}
        />
        <StatTile
          label="Cluster reviews"
          value={model.review_count}
          hint={model.low_confidence ? "low confidence (<50)" : "sufficient"}
          trend={model.low_confidence ? "down" : "flat"}
        />
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-dawn-400/50 bg-dawn-400/10 px-4 py-2 text-sm text-forest-800">
          {error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="Adjust aspect levers"
          subtitle="Slider range -1.0 … +1.0 (step 0.1), capped so scores stay in 1–5"
        >
          {noData ? (
            <p className="text-sm text-forest-600">
              No data for this platform — sliders are disabled.
            </p>
          ) : (
            <div className="space-y-4">
              {ASPECTS.map((aspect) => {
                const dw = model.driver_weights.find((d) => d.aspect === aspect);
                const disabled = !dw || !dw.available;
                const value = deltas[aspect] ?? 0;
                return (
                  <div key={aspect}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium text-forest-800">
                        {aspect.replace(/_/g, " ")}
                      </span>
                      <span className="tabular-nums text-forest-600">
                        {value >= 0 ? "+" : ""}
                        {value.toFixed(1)}
                        {disabled && (
                          <span className="ml-2 text-xs text-dawn-500">
                            no data
                          </span>
                        )}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={-1}
                      max={1}
                      step={0.1}
                      value={value}
                      disabled={disabled}
                      aria-label={`${aspect} slider`}
                      onChange={(e) => onSlider(aspect, Number(e.target.value))}
                      className="w-full accent-forest-600 disabled:opacity-40"
                    />
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card
          title="Driver weights"
          subtitle="Ranked by |weight| — change in overall rating per +1 aspect point (90% CI)"
        >
          <ul className="space-y-2">
            {rankedWeights.map((d) => (
              <li
                key={d.aspect}
                className="flex items-center justify-between rounded-lg bg-mist-100 px-3 py-2 text-sm"
              >
                <span className="font-medium text-forest-800">
                  {d.aspect.replace(/_/g, " ")}
                </span>
                <span className="tabular-nums text-forest-600">
                  {d.available ? (
                    <>
                      {d.weight.toFixed(3)}{" "}
                      <span className="text-xs text-forest-500">
                        [{d.lower.toFixed(2)}, {d.upper.toFixed(2)}]
                      </span>
                    </>
                  ) : (
                    <span className="text-dawn-500">no data</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
