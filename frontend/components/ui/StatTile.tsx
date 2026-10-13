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
        // Frosted glass stat surface with an interactive-3D hover lift/tilt.
        "glass-panel glass-lift group relative overflow-hidden bg-mist-white/70",
        className,
      )}
    >
      <div className="glass-lift-inner relative p-5">
        {/* Mountain/forest accent bar (leaf -> moss -> amber). */}
        <span
          aria-hidden
          className="absolute inset-x-0 top-0 h-1 opacity-90"
          style={{
            backgroundImage:
              "linear-gradient(90deg, var(--pp-leaf) 0%, var(--pp-moss) 55%, var(--pp-amber) 100%)",
          }}
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
    </div>
  );
}
