"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import { ReviewCountsTable } from "@/components/market-radar/ReviewCountsTable";
import { TrendsPanel } from "@/components/market-radar/TrendsPanel";
import { DecompositionPanel } from "@/components/market-radar/DecompositionPanel";
import {
  api,
  type PropertyCounts,
  type TrendsResponse,
  type DecompositionResponse,
} from "@/lib/api";
import snapshot from "@/lib/marketRadarSnapshot.json";
import analytics from "@/lib/analyticsSnapshot.json";

const SNAPSHOT = snapshot.properties as PropertyCounts[];
const TRENDS = analytics.trends as unknown as TrendsResponse;
const DECOMP = analytics.decomposition as unknown as DecompositionResponse;
const HOME_ID = (analytics.homeProperty as { id: string }).id;

export default function MarketRadarPage() {
  const [properties, setProperties] = useState<PropertyCounts[]>(SNAPSHOT);
  const [trends, setTrends] = useState<TrendsResponse>(TRENDS);
  const [decomp, setDecomp] = useState<DecompositionResponse>(DECOMP);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .reviewCounts()
      .then((res) => {
        if (active) {
          setProperties(res.properties);
          setLive(true);
        }
      })
      .catch(() => {
        /* keep the bundled snapshot when the API is unreachable */
      });
    api.trends().then((t) => active && setTrends(t)).catch(() => {});
    api
      .decomposition()
      .then((d) => active && setDecomp(d))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const totalReviews = properties.reduce((sum, p) => sum + p.total, 0);
  const totalMissing = properties.reduce(
    (sum, p) => sum + p.missing_source_url,
    0,
  );
  const platforms = new Set<string>();
  properties.forEach((p) =>
    Object.keys(p.per_platform).forEach((k) => platforms.add(k)),
  );

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar"
        title="Market Radar"
        description="Per-property, per-platform review coverage for your Mussoorie cluster. Counts refresh after each collection job."
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

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

      <div className="mb-6">
        <TrendsPanel data={trends} />
      </div>

      <div className="mb-6">
        <DecompositionPanel data={decomp} homePropertyId={HOME_ID} />
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
