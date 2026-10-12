/**
 * A tiny two-series line chart used by the Proof-of-Impact and Forecast panels.
 * Pure SVG so it renders in tests without a chart library.
 */
export interface Series {
  label: string;
  color: string;
  points: { x: string; y: number }[];
}

export function MiniTrend({
  series,
  height = 160,
  yMin,
  yMax,
}: {
  series: Series[];
  height?: number;
  yMin?: number;
  yMax?: number;
}) {
  const allY = series.flatMap((s) => s.points.map((p) => p.y));
  const lo = yMin ?? Math.min(...allY, 0);
  const hi = yMax ?? Math.max(...allY, 1);
  const span = hi - lo || 1;
  const width = 420;
  const pad = 24;
  const maxLen = Math.max(...series.map((s) => s.points.length), 1);

  function path(points: { x: string; y: number }[]) {
    return points
      .map((p, i) => {
        const x = pad + (i / Math.max(maxLen - 1, 1)) * (width - 2 * pad);
        const y = height - pad - ((p.y - lo) / span) * (height - 2 * pad);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  return (
    <div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label="trend chart"
      >
        <line
          x1={pad}
          y1={height - pad}
          x2={width - pad}
          y2={height - pad}
          stroke="#cbd9cd"
        />
        {series.map((s) => (
          <path
            key={s.label}
            d={path(s.points)}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
          />
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-forest-600">
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-4 rounded"
              style={{ backgroundColor: s.color }}
            />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}
