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
  down: "text-dawn-500",
  flat: "text-forest-500/70",
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
        "rounded-2xl border border-mist-300 bg-mist-50 p-5 shadow-tile",
        className,
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-forest-600/70">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-forest-800">{value}</p>
      {(hint || trend) && (
        <p className="mt-1 flex items-center gap-1 text-xs text-forest-600/80">
          {trend && (
            <span className={trendClasses[trend]}>{trendGlyph[trend]}</span>
          )}
          {hint}
        </p>
      )}
    </div>
  );
}
