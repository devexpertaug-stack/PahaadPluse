import { palette } from "@/lib/theme";

export interface Series {
  label: string;
  color: string;
  points: (number | null)[];
  /** Optional 90% interval band [lower, upper] aligned to points. */
  band?: { lower: number; upper: number }[];
}

export interface LineChartProps {
  labels: string[];
  series: Series[];
  height?: number;
  yMin?: number;
  yMax?: number;
  yLabel?: string;
  ariaLabel?: string;
}

/**
 * Dependency-free SVG multi-series line chart with an optional credible-interval
 * band. Styled to the hill-town palette.
 */
export function LineChart({
  labels,
  series,
  height = 220,
  yMin,
  yMax,
  yLabel,
  ariaLabel,
}: LineChartProps) {
  const width = 640;
  const padL = 44;
  const padR = 16;
  const padT = 12;
  const padB = 34;
  const innerW = width - padL - padR;
  const innerH = height - padT - padB;

  const allValues = series
    .flatMap((s) => s.points)
    .filter((v): v is number => v !== null);
  const bandValues = series.flatMap((s) =>
    (s.band ?? []).flatMap((b) => [b.lower, b.upper]),
  );
  const dataMin = Math.min(...allValues, ...bandValues);
  const dataMax = Math.max(...allValues, ...bandValues);
  const lo = yMin ?? (Number.isFinite(dataMin) ? dataMin : 0);
  const hi = yMax ?? (Number.isFinite(dataMax) ? dataMax : 1);
  const span = hi - lo || 1;

  const n = labels.length;
  const x = (i: number) => padL + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const y = (v: number) => padT + innerH - ((v - lo) / span) * innerH;

  const gridLines = 4;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel ?? "line chart"}
      className="w-full"
    >
      {/* grid */}
      {Array.from({ length: gridLines + 1 }).map((_, i) => {
        const gy = padT + (i / gridLines) * innerH;
        const val = hi - (i / gridLines) * span;
        return (
          <g key={i}>
            <line
              x1={padL}
              x2={width - padR}
              y1={gy}
              y2={gy}
              stroke={palette.mist.haze}
              strokeWidth={1}
            />
            <text x={8} y={gy + 4} fontSize={10} fill={palette.ink}>
              {val.toFixed(span < 5 ? 1 : 0)}
            </text>
          </g>
        );
      })}

      {/* bands */}
      {series.map((s, si) =>
        s.band ? (
          <polygon
            key={`band-${si}`}
            fill={s.color}
            fillOpacity={0.12}
            stroke="none"
            points={[
              ...s.band.map((b, i) => `${x(i)},${y(b.upper)}`),
              ...s.band
                .map((b, i) => `${x(i)},${y(b.lower)}`)
                .reverse(),
            ].join(" ")}
          />
        ) : null,
      )}

      {/* lines */}
      {series.map((s, si) => {
        const path = s.points
          .map((v, i) =>
            v === null ? null : `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`,
          )
          .filter(Boolean)
          .join(" ");
        return (
          <g key={`line-${si}`}>
            <path d={path} fill="none" stroke={s.color} strokeWidth={2} />
            {s.points.map((v, i) =>
              v === null ? null : (
                <circle key={i} cx={x(i)} cy={y(v)} r={2.5} fill={s.color} />
              ),
            )}
          </g>
        );
      })}

      {/* x labels (sparse) */}
      {labels.map((lab, i) => {
        const show = n <= 8 || i % Math.ceil(n / 8) === 0 || i === n - 1;
        if (!show) return null;
        return (
          <text
            key={i}
            x={x(i)}
            y={height - 10}
            fontSize={9}
            fill={palette.ink}
            textAnchor="middle"
          >
            {lab.length > 7 ? lab.slice(5) : lab}
          </text>
        );
      })}

      {yLabel && (
        <text
          x={12}
          y={padT - 2}
          fontSize={9}
          fill={palette.forest.mid}
          fontWeight={600}
        >
          {yLabel}
        </text>
      )}
    </svg>
  );
}
