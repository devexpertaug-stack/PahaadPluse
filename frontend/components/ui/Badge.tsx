import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "forest" | "pine" | "dawn" | "sky" | "slate" | "neutral";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClasses: Record<Tone, string> = {
  forest: "bg-forest-100 text-forest-800 border-forest-200",
  pine: "bg-pine-400/20 text-pine-600 border-pine-400/40",
  dawn: "bg-dawn-400/25 text-dawn-600 border-dawn-400/50",
  sky: "bg-sky-100 text-sky-700 border-sky-200",
  slate: "bg-slate-100 text-slate-600 border-slate-200",
  neutral: "bg-mist-200 text-slate-600 border-mist-300",
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
