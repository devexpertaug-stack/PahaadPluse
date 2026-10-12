"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/ui";
import { LineChart, type Series } from "@/components/charts/LineChart";
import { Drilldown } from "@/components/common/Drilldown";
import { ASPECTS, type TrendsResponse } from "@/lib/api";
import { palette } from "@/lib/theme";

export function TrendsPanel({ data }: { data: TrendsResponse }) {
  const [aspect, setAspect] = useState<string>(ASPECTS[0]);

  const trend = useMemo(
    () => data.trends.find((t) => t.aspect === aspect) ?? data.trends[0],
    [data, aspect],
  );

  const labels = trend.buckets.map((b) => b.period);
  const series: Series[] = [
    {
      label: "Positive",
      color: palette.forest.bright,
      points: trend.buckets.map((b) => b.positive),
    },
    {
      label: "Neutral",
      color: palette.dawn,
      points: trend.buckets.map((b) => b.neutral),
    },
    {
      label: "Negative",
      color: palette.alert.DEFAULT,
      points: trend.buckets.map((b) => b.negative),
    },
  ];

  const complaintSeries: Series[] = [
    {
      label: "Complaint %",
      color: palette.alert.DEFAULT,
      points: trend.buckets.map((b) => b.complaint_percentage),
    },
  ];

  return (
    <Card
      title="Aspect sentiment trends"
      subtitle={`Monthly IST periods · ${data.start} → ${data.end} · platforms: ${data.platforms.join(", ")}`}
    >
      <div className="mb-4 flex flex-wrap gap-2">
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

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <p className="mb-1 text-sm font-medium text-forest-700">
            Mention counts
          </p>
          <LineChart
            labels={labels}
            series={series}
            ariaLabel={`${aspect} mention counts`}
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
          </div>
        </div>
        <div>
          <p className="mb-1 text-sm font-medium text-forest-700">
            Category complaint trend (negative / total)
          </p>
          <LineChart
            labels={labels}
            series={complaintSeries}
            yMin={0}
            yLabel="%"
            ariaLabel={`${aspect} complaint percentage`}
          />
          <p className="mt-2 text-xs text-forest-600">
            Periods with no mentions show a no-data gap; percentages are to 1
            decimal place.
          </p>
        </div>
      </div>

      <div className="mt-6 border-t border-mist-200 pt-4">
        <p className="mb-2 text-sm font-medium text-forest-700">
          Every number is clickable — drill down to the source reviews
        </p>
        <div className="flex flex-wrap gap-2 text-sm">
          {trend.buckets
            .filter((b) => b.negative > 0)
            .slice(-8)
            .map((b) => (
              <span
                key={b.period}
                className="rounded-lg border border-mist-300 bg-mist-50 px-2 py-1"
              >
                <span className="text-xs text-forest-500">{b.period}: </span>
                <Drilldown
                  metric={`${aspect} negative mentions · ${b.period}`}
                  kind="count"
                  clicked_value={b.negative}
                  aspect={aspect}
                  label="negative"
                  period={b.period}
                  granularity={data.granularity}
                  platform={data.platforms}
                >
                  {b.negative} negative
                </Drilldown>
              </span>
            ))}
        </div>
      </div>
    </Card>
  );
}
