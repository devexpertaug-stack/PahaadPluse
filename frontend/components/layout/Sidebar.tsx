"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { brand, navItems, type SubsystemGroup } from "@/lib/theme";
import { cn } from "@/lib/cn";

const groupOrder: SubsystemGroup[] = [
  "Overview",
  "Market Radar",
  "Destination Lens",
  "In-Stay Sentinel",
  "Guest Compass",
  "Bhasha Concierge",
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="glass-panel--dark relative z-20 flex min-h-screen w-64 shrink-0 flex-col rounded-none border-y-0 border-l-0 text-mist-100"
      style={{
        backgroundColor: "rgba(27, 59, 42, 0.72)",
        backgroundImage:
          "linear-gradient(165deg, rgba(36,59,53,0.92) 0%, rgba(27,59,42,0.9) 50%, rgba(12,20,16,0.95) 100%)",
      }}
    >
      <div className="px-5 py-6">
        <Link href="/dashboard" className="flex items-center gap-3">
          <span
            aria-hidden
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-mist-50/10 text-lg"
          >
            🏔️
          </span>
          <span>
            <span className="block font-display text-lg font-bold leading-tight tracking-tight">
              {brand.name}
            </span>
            <span className="block text-xs text-mist-200/80">
              {brand.region}
            </span>
          </span>
        </Link>
      </div>
      <div className="mx-5 h-px bg-mist-50/15" />
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {groupOrder.map((group) => {
          const items = navItems.filter((item) => item.group === group);
          if (items.length === 0) return null;
          return (
            <div key={group} className="mb-5">
              <p className="px-3 pb-1 text-[0.65rem] font-semibold uppercase tracking-widest text-mist-200/60">
                {group}
              </p>
              <ul className="space-y-0.5">
                {items.map((item) => {
                  const active =
                    item.href === "/dashboard"
                      ? pathname === "/dashboard"
                      : pathname.startsWith(item.href);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "block rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                          active
                            ? "bg-pp-leaf/20 text-mist-50 shadow-sm ring-1 ring-inset ring-pp-leaf/50"
                            : "text-mist-200/85 hover:bg-pp-leaf/10 hover:text-mist-50",
                        )}
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>
      <div className="px-5 py-4 text-xs text-mist-200/60">
        {brand.tagline}
      </div>
    </aside>
  );
}
