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
        "rounded-2xl border border-mist-300 bg-mist-white shadow-tile",
        "transition-shadow duration-200 hover:shadow-ridge",
        className,
      )}
      {...props}
    >
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
        <footer className="border-t border-mist-200 px-5 py-3 text-sm text-slate-500">
          {footer}
        </footer>
      )}
    </section>
  );
}
