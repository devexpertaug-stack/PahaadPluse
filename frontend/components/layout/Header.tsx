"use client";

import { usePathname } from "next/navigation";
import { navItems } from "@/lib/theme";
import { Badge } from "@/components/ui/Badge";

export function Header() {
  const pathname = usePathname();
  const active =
    navItems.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    ) ?? navItems[0];

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-mist-300 bg-mist-white/85 px-6 py-4 backdrop-blur-md">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-sky-600">
          {active.group}
        </p>
        <h2 className="font-display text-lg font-semibold text-forest-800">
          {active.label}
        </h2>
      </div>
      <div className="flex items-center gap-3">
        <Badge tone="sky">Demo mode</Badge>
        <span className="hidden text-sm text-slate-500 sm:inline">
          Local fallbacks active
        </span>
      </div>
    </header>
  );
}
