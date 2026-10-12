"use client";

import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import { ReviewCountsTable } from "@/components/market-radar/ReviewCountsTable";
import { TrendsPanel } from "@/components/market-radar/TrendsPanel";
import { DecompositionPanel } from "@/components/market-radar/DecompositionPanel";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import {
  api,
  type ReviewCountsResponse,
  type TrendsResponse,
  type DecompositionResponse,
} from "@/lib/api";

// The home property id drives the decomposition panel's highlighting. It is
// derived from the live review counts (the first/home property) rather than a
// baked snapshot so the panel always tracks the real cluster.
export default function MarketRadarPage() {
  const counts = useLiveData<ReviewCountsResponse>(() => api.reviewCounts(), {
    isEmpty: (d) => d.properties.length === 0,
  });
  const trends = useLiveData<TrendsResponse>(() => api.trends());
  const decomp = useLiveData<DecompositionResponse>(() => api.decomposition());

  const badge = liveBadgeProps(counts.status);
  const properties = counts.data?.properties ?? [];
  const totalReviews = properties.reduce((sum, p) => sum + p.total, 0);
  const totalMissing = properties.reduce(
    (sum, p) => sum + p.missing_source_url,
    0,
  );
  const platforms = new Set<string>();
  properties.forEach((p) =>
    Object.keys(p.per_platform).forEach((k) => platforms.add(k)),
  );
  const homeId = properties[0]?.property_id ?? "";

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar"
        title="Market Radar"
        description="Per-property, per-platform review coverage for your Mussoorie cluster. Counts refresh after each collection job."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <LoadState
        status={counts.status}
        onRetry={counts.reload}
        emptyBody="The backend returned no tracked properties. Seed or ingest reviews to populate Market Radar."
      >
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="Properties tracked" value={properties.length} hint="cluster" />
          <StatTile label="Platforms" value={platforms.size} hint="review sources" />
          <StatTile label="Reviews collected" value={totalReviews} trend="up" hint="across cluster" />
          <StatTile
            label="Source URL unavailable"
            value={totalMissing}
            trend={totalMissing > 0 ? "down" : "flat"}
            hint="pseudonymised, URL missing"
          />
        </div>

        <Card
          title="Review counts by property and platform"
          subtitle="Updates after a collection job completes (Req 1.10)"
          className="mb-6"
        >
          <ReviewCountsTable properties={properties} />
        </Card>
      </LoadState>

      <div className="mb-6">
        <LoadState status={trends.status} onRetry={trends.reload}>
          {trends.data && <TrendsPanel data={trends.data} />}
        </LoadState>
      </div>

      <div className="mb-6">
        <LoadState status={decomp.status} onRetry={decomp.reload}>
          {decomp.data && (
            <DecompositionPanel data={decomp.data} homePropertyId={homeId} />
          )}
        </LoadState>
      </div>

      <Card
        title="Responsible collection"
        subtitle="How this cluster's reviews are gathered"
      >
        <ul className="list-disc space-y-2 pl-5 text-sm text-forest-700">
          <li>
            Reviewer names are pseudonymised with a salted hash; raw names are
            never stored.
          </li>
          <li>
            Public source URLs are retained; reviews without one are shown as
            <span className="font-medium"> &ldquo;source URL unavailable&rdquo;</span>.
          </li>
          <li>
            Crawling honours robots.txt, a 1 request / 5s rate limit and a
            PahadPulse contact user-agent.
          </li>
        </ul>
      </Card>
    </div>
  );
}
