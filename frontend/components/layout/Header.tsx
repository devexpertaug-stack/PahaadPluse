"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { navItems } from "@/lib/theme";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { clearSession, getUser, type SessionUser } from "@/lib/auth";

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);

  // Read the session user on the client only (avoids SSR localStorage access).
  useEffect(() => {
    setUser(getUser());
  }, []);

  const active =
    navItems.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    ) ?? navItems[0];

  function handleLogout() {
    clearSession();
    router.replace("/login");
  }

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
        {user ? (
          <>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-forest-800">
                {user.display_name}
              </p>
              <p className="text-xs text-slate-500">
                {user.property_name} · {user.role}
              </p>
            </div>
            <Badge tone="forest">{user.property_name}</Badge>
            <Button variant="secondary" size="sm" onClick={handleLogout}>
              Log out
            </Button>
          </>
        ) : (
          <Badge tone="sky">Demo mode</Badge>
        )}
      </div>
    </header>
  );
}
