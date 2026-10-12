import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface StatTileProps {
  label: string;
  value: ReactNode;
  hint?: string;
  trend?: "up" | "down" | "flat";
  className?: string;
}

const trendClasses: Record<NonNullable<StatTileProps["trend"]>, string> = {
  up: "text-forest-600",
  down: "text-dawn-600",
  flat: "text-slate-400",
};

const trendGlyph: Record<NonNullable<StatTileProps["trend"]>, string> = {
  up: "▲",
  down: "▼",
  flat: "■",
};

export function StatTile({
  label,
  value,
  hint,
  trend,
  className,
}: StatTileProps) {
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-mist-300 bg-mist-white p-5 shadow-tile",
        "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-ridge",
        className,
      )}
    >
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-1 bg-dawn-ridge opacity-80"
      />
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-2 font-display text-3xl font-bold text-forest-800">
        {value}
      </p>
      {(hint || trend) && (
        <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
          {trend && (
            <span className={trendClasses[trend]}>{trendGlyph[trend]}</span>
          )}
          {hint}
        </p>
      )}
    </div>
  );
}
