import { palette } from "@/lib/theme";

export interface SparklineProps {
  points: (number | null)[];
  color?: string;
  width?: number;
  height?: number;
  ariaLabel?: string;
}

/** A tiny inline trend sparkline (dependency-free SVG). */
export function Sparkline({
  points,
  color = palette.forest.bright,
  width = 120,
  height = 32,
  ariaLabel,
}: SparklineProps) {
  const vals = points.filter((v): v is number => v !== null);
  const lo = vals.length ? Math.min(...vals) : 0;
  const hi = vals.length ? Math.max(...vals) : 1;
  const span = hi - lo || 1;
  const n = points.length;
  const x = (i: number) => (n <= 1 ? width / 2 : (i / (n - 1)) * width);
  const y = (v: number) => height - ((v - lo) / span) * height;
  const path = points
    .map((v, i) => (v === null ? null : `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`))
    .filter(Boolean)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel ?? "sparkline"}
      className="inline-block"
      width={width}
      height={height}
    >
      <path d={path} fill="none" stroke={color} strokeWidth={1.8} />
    </svg>
  );
}
