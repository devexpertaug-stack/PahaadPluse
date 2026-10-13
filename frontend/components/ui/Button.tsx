import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClasses: Record<Variant, string> = {
  // Deep forest fill with a glassy highlight and a tactile lift on hover.
  primary:
    "bg-pp-forest text-mist-50 shadow-glass ring-1 ring-inset ring-white/10 hover:-translate-y-0.5 hover:bg-pp-slate hover:shadow-glow focus-visible:ring-pp-leaf",
  // Frosted translucent surface that reads as glass over the scenery.
  secondary:
    "border border-pp-mist/70 bg-mist-white/60 text-forest-800 backdrop-blur-md hover:-translate-y-0.5 hover:border-pp-leaf/70 hover:bg-mist-white/80 focus-visible:ring-pp-leaf",
  ghost:
    "bg-transparent text-forest-700 hover:bg-pp-mist/40 focus-visible:ring-forest-400",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold",
        "transition-all duration-150",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
