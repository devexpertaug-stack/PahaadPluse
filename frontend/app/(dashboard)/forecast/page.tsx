"use client";

import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import { MiniTrend } from "@/components/common/MiniTrend";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { api, type ForecastResponse, type AspectForecast } from "@/lib/api";
import { palette } from "@/lib/theme";

export default function ForecastPage() {
  const { status, data, reload } = useLiveData<ForecastResponse>(
    () => api.forecast(),
    { isEmpty: (d) => d.forecasts.length === 0 },
  );
  const badge = liveBadgeProps(status);

  const withWarnings =
    data?.forecasts.filter((f) => f.early_warnings.length > 0) ?? [];
  const shown = (withWarnings.length ? withWarnings : data?.forecasts ?? []).slice(
    0,
    6,
  );

  return (
    <div>
      <PageHeader
        eyebrow="In-Stay Sentinel · F11"
        title="Complaint Forecasting"
        description="A 4-week-ahead weekly forecast of negative aspect-mention counts per aspect, with an 80% prediction interval built from seasonal components and recent changepoints. Early warnings fire when the forecast upper bound exceeds the trailing 12-week mean by more than 50%. Accuracy is the mean absolute error over the most recent 8 held-out weeks."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <LoadState status={status} onRetry={reload}>
      {data && data.early_warnings.length > 0 && (
        <Card
          title="Early warnings"
          subtitle="Forecast upper bound exceeds the trailing mean by >50%"
          className="mb-6"
        >
          <ul className="space-y-2">
            {data.early_warnings.map((w, i) => (
              <li
                key={i}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-dawn-400/40 bg-dawn-400/10 px-3 py-2 text-sm text-forest-800"
              >
                <Badge tone="dawn">{w.aspect}</Badge>
                <span>
                  week of {w.week}: forecast up to {w.forecast_upper.toFixed(1)}{" "}
                  negatives vs trailing mean {w.trailing_mean.toFixed(1)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="space-y-6">
        {shown.map((f) => (
          <ForecastCard key={f.aspect} forecast={f} />
        ))}
      </div>
      </LoadState>
    </div>
  );
}

function ForecastCard({ forecast: f }: { forecast: AspectForecast }) {
  const historyPoints = f.history.map((h) => ({ x: h.week, y: h.negatives }));
  const forecastPoints = f.forecast.map((p) => ({ x: p.week, y: p.point }));
  const upperPoints = f.forecast.map((p) => ({ x: p.week, y: p.upper }));
  const lowerPoints = f.forecast.map((p) => ({ x: p.week, y: p.lower }));

  return (
    <Card
      title={`${f.aspect} — weekly negative mentions`}
      subtitle={`trailing mean ${f.trailing_mean.toFixed(1)}`}
    >
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatTile
          label="8-week MAE"
          value={f.mae != null ? f.mae.toFixed(2) : "n/a"}
          hint="held-out accuracy"
        />
        <StatTile
          label="Early warnings"
          value={f.early_warnings.length}
          trend={f.early_warnings.length ? "down" : "flat"}
        />
        <StatTile
          label="Next-week forecast"
          value={f.forecast[0]?.point.toFixed(1) ?? "—"}
          hint="80% PI"
        />
      </div>
      <MiniTrend
        series={[
          { label: "History", color: palette.forest.DEFAULT, points: historyPoints },
          { label: "Forecast", color: palette.dawn, points: forecastPoints },
          { label: "80% upper", color: palette.sky.bright, points: upperPoints },
          { label: "80% lower", color: palette.sky.bright, points: lowerPoints },
        ]}
      />
    </Card>
  );
}
