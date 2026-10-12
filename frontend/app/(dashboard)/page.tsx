"use client";

import Link from "next/link";
import { PageHeader, StatTile, Card, Button, Badge } from "@/components/ui";
import { liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { navItems } from "@/lib/theme";
import {
  api,
  type ReviewCountsResponse,
  type SentinelMetrics,
  type BoardResponse,
} from "@/lib/api";

export default function MetricsOverviewPage() {
  const subsystemLinks = navItems.filter((item) => item.href !== "/");

  // The overview is driven by live backend aggregates — no baked placeholders.
  const counts = useLiveData<ReviewCountsResponse>(() => api.reviewCounts());
  const sentinel = useLiveData<SentinelMetrics>(() => api.sentinelMetrics());
  const board = useLiveData<BoardResponse>(() => api.board());

  const badge = liveBadgeProps(counts.status);
  const properties = counts.data?.properties ?? [];
  const totalReviews = properties.reduce((sum, p) => sum + p.total, 0);
  const openComplaints = sentinel.data?.open_complaints;
  const highRisk = board.data?.rows.filter((r) => r.high_risk).length;

  const show = (status: string, value: number | undefined) =>
    status === "ready" && value != null ? value.toLocaleString("en-IN") : "—";

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Metrics Overview"
        description="A single pane over every PahadPulse subsystem, driven live by the seeded Forest Season Resort cluster. Open any subsystem for the full live view."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Properties tracked"
          value={show(counts.status, properties.length)}
          hint="Mussoorie cluster"
          trend="flat"
        />
        <StatTile
          label="Reviews analysed"
          value={show(counts.status, totalReviews)}
          hint="Market Radar pipeline"
          trend="up"
        />
        <StatTile
          label="Open complaints"
          value={show(sentinel.status, openComplaints)}
          hint="In-Stay Sentinel"
          trend="flat"
        />
        <StatTile
          label="High-risk checkouts"
          value={show(board.status, highRisk)}
          hint="Checkout Shield"
          trend="flat"
        />
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-forest-800">
          Explore the platform
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {subsystemLinks.map((item) => (
            <Card
              key={item.href}
              title={item.label}
              subtitle={item.group}
              footer={
                <Link href={item.href}>
                  <Button variant="ghost" size="sm">
                    Open {item.label} →
                  </Button>
                </Link>
              }
            >
              <p className="text-sm text-forest-700">{item.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
