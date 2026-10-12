"use client";

import { useMemo, useState } from "react";
import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import {
  api,
  ASPECTS,
  PLATFORMS,
  type WhatIfModel,
  type WhatIfProjection,
} from "@/lib/api";

export default function WhatIfPage() {
  const [platform, setPlatform] = useState<string>(PLATFORMS[0]);
  const [deltas, setDeltas] = useState<Record<string, number>>({});
  const [projection, setProjection] = useState<WhatIfProjection | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { status, data: model, reload } = useLiveData<WhatIfModel>(
    () => api.whatIfModel(platform),
    { deps: [platform] },
  );
  const badge = liveBadgeProps(status);

  // Reset the sliders whenever the platform (and therefore the live model)
  // changes.
  const rankedWeights = useMemo(
    () =>
      model
        ? [...model.driver_weights].sort(
            (a, b) => Math.abs(b.weight) - Math.abs(a.weight),
          )
        : [],
    [model],
  );

  function runProjection(next: Record<string, number>) {
    setError(null);
    api
      .whatIfProject(platform, next)
      .then(setProjection)
      .catch(() => setError("Projection failed; the backend is unreachable."));
  }

  function onSlider(aspect: string, value: number) {
    const next = { ...deltas, [aspect]: value };
    setDeltas(next);
    runProjection(next);
  }

  function selectPlatform(p: string) {
    setPlatform(p);
    setDeltas({});
    setProjection(null);
  }

  const noData = model
    ? model.driver_weights.every((d) => !d.available)
    : true;

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F1"
        title="Rating What-If Simulator"
        description="Model the projected overall rating and cluster rank before you make a change. Driver weights come from all cluster reviews on the selected platform."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        {PLATFORMS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => selectPlatform(p)}
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

      <LoadState status={status} onRetry={reload}>
        {model && (
          <>
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
                value={
                  projection && projection.projected_rank
                    ? `#${projection.projected_rank}`
                    : "—"
                }
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
                      const dw = model.driver_weights.find(
                        (d) => d.aspect === aspect,
                      );
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
                            onChange={(e) =>
                              onSlider(aspect, Number(e.target.value))
                            }
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
          </>
        )}
      </LoadState>
    </div>
  );
}
