import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  subtitle?: ReactNode;
  footer?: ReactNode;
}

export function Card({
  title,
  subtitle,
  footer,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <section
      className={cn(
        // Frosted mountain/forest glass surface (FEAT-001 .glass-panel) with a
        // tasteful interactive-3D hover lift/tilt via .glass-lift.
        "glass-panel glass-lift group/card bg-mist-white/70",
        className,
      )}
      {...props}
    >
      <div className="glass-lift-inner">
        {(title || subtitle) && (
          <header className="px-5 pt-5">
            {title && (
              <h3 className="font-display text-base font-semibold text-forest-800">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
            )}
          </header>
        )}
        <div className="px-5 py-4">{children}</div>
        {footer && (
          <footer className="border-t border-mist-200/70 px-5 py-3 text-sm text-slate-500">
            {footer}
          </footer>
        )}
      </div>
    </section>
  );
}
