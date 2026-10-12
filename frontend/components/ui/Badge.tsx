import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "forest" | "pine" | "dawn" | "neutral";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClasses: Record<Tone, string> = {
  forest: "bg-forest-100 text-forest-800 border-forest-200",
  pine: "bg-pine-400/15 text-pine-600 border-pine-400/30",
  dawn: "bg-dawn-400/20 text-forest-800 border-dawn-400/40",
  neutral: "bg-mist-200 text-forest-700 border-mist-300",
};

export function Badge({ tone = "forest", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
