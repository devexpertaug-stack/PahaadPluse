import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  actions?: ReactNode;
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
}: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-widest text-pine-500">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-2xl font-semibold text-forest-800">{title}</h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm text-forest-600/90">
            {description}
          </p>
        )}
        <div className="ridge-divider mt-4 w-24" />
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
