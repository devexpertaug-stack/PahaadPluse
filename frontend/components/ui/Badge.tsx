import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "forest" | "pine" | "dawn" | "sky" | "slate" | "neutral";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClasses: Record<Tone, string> = {
  // Default forest tone keeps the text-forest-800 class StatTile.test asserts,
  // now on a translucent frosted pill to match the glassmorphism system.
  forest: "bg-forest-100/70 text-forest-800 border-forest-200/70 backdrop-blur-sm",
  pine: "bg-pine-400/20 text-pine-600 border-pine-400/40 backdrop-blur-sm",
  dawn: "bg-dawn-400/25 text-dawn-600 border-dawn-400/50 backdrop-blur-sm",
  sky: "bg-sky-100/70 text-sky-700 border-sky-200/70 backdrop-blur-sm",
  slate: "bg-slate-100/70 text-slate-600 border-slate-200/70 backdrop-blur-sm",
  neutral: "bg-mist-200/70 text-slate-600 border-mist-300/70 backdrop-blur-sm",
};

export function Badge({ tone = "forest", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide",
        "transition-colors",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
