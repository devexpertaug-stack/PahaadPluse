"use client";

import { usePathname } from "next/navigation";
import { navItems } from "@/lib/theme";
import { Badge } from "@/components/ui/Badge";

export function Header() {
  const pathname = usePathname();

  const active =
    navItems.find((item) =>
      item.href === "/dashboard"
        ? pathname === "/dashboard"
        : pathname.startsWith(item.href),
    ) ?? navItems[0];

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-pp-mist/60 bg-mist-white/70 px-6 py-4 backdrop-blur-xl backdrop-saturate-150">
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
      </div>
    </header>
  );
}
