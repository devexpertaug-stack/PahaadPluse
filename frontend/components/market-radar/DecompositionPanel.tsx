"use client";

import { useMemo, useState } from "react";
import { Card, Badge } from "@/components/ui";
import { LineChart, type Series } from "@/components/charts/LineChart";
import { ASPECTS, type DecompositionResponse } from "@/lib/api";
import { palette } from "@/lib/theme";

export function DecompositionPanel({
  data,
  homePropertyId,
}: {
  data: DecompositionResponse;
  homePropertyId: string;
}) {
  const [aspect, setAspect] = useState<string>(ASPECTS[0]);

  const cells = useMemo(
    () =>
      data.cells
        .filter((c) => c.property_id === homePropertyId && c.aspect === aspect)
        .sort((a, b) => a.month.localeCompare(b.month)),
    [data, aspect, homePropertyId],
  );

  const labels = cells.map((c) => c.month);
  const anyUnreliable = cells.some((c) => c.unreliable);
  const anyInsufficient = cells.some((c) => c.insufficient_data);

  const series: Series[] = [
    {
      label: "Market-wide",
      color: palette.pine,
      points: cells.map((c) => c.market_wide.point),
      band: cells.map((c) => ({
        lower: c.market_wide.lower,
        upper: c.market_wide.upper,
      })),
    },
    {
      label: "Modelled property score",
      color: palette.forest.bright,
      points: cells.map((c) => c.modelled_score),
    },
  ];

  return (
    <Card
      title="Market-wide vs property-specific decomposition"
      subtitle={`Hierarchical fit · ${new Date(data.fitted_at).toLocaleString()} · cluster of ${data.cluster_size}`}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {ASPECTS.map((a) => (
          <button
            key={a}
            type="button"
            onClick={() => setAspect(a)}
            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
              aspect === a
                ? "border-forest-600 bg-forest-100 text-forest-800"
                : "border-mist-300 bg-mist-50 text-forest-600 hover:bg-mist-100"
            }`}
          >
            {a.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        {anyUnreliable && <Badge tone="dawn">R-hat &gt; 1.05 · unreliable</Badge>}
        {anyInsufficient && (
          <Badge tone="neutral">insufficient data (shown, not hidden)</Badge>
        )}
        {data.failure && (
          <Badge tone="dawn">
            refit failed — serving fit from{" "}
            {data.stale_timestamp
              ? new Date(data.stale_timestamp).toLocaleString()
              : "last run"}
          </Badge>
        )}
      </div>

      <LineChart
        labels={labels}
        series={series}
        yMin={1}
        yMax={5}
        yLabel="score"
        ariaLabel={`${aspect} decomposition`}
      />
      <div className="mt-2 flex gap-4 text-xs text-forest-600">
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: s.color }}
            />
            {s.label}
          </span>
        ))}
        <span>Shaded band = 90% credible interval.</span>
      </div>
    </Card>
  );
}
