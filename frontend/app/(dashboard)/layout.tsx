import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { SessionGate } from "@/components/auth/SessionGate";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <SessionGate>
      <AppShell>{children}</AppShell>
    </SessionGate>
  );
}
