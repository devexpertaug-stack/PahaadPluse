"use client";

import { PageHeader, Card, Badge } from "@/components/ui";
import { Sparkline } from "@/components/charts/Sparkline";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { api, type GapFinderResponse } from "@/lib/api";

export default function GapFinderPage() {
  const { status, data, reload } = useLiveData<GapFinderResponse>(
    () => api.gapFinder(),
    { isEmpty: (d) => d.themes.length === 0 },
  );
  const badge = liveBadgeProps(status);

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F6"
        title="Market Gap Finder"
        description="Issue themes ranked by how many cluster properties run above the destination median negative share, then by total negatives. Themes negative at 60%+ of properties are flagged as market gaps."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <LoadState
        status={status}
        onRetry={reload}
        emptyBody="The cluster has no negative-theme gaps to rank yet. Seed or ingest reviews to populate the Gap Finder."
      >
        <div className="space-y-4">
          {data?.themes.map((theme) => (
            <Card
              key={theme.aspect}
              title={theme.aspect.replace(/_/g, " ")}
              subtitle={`Destination median negative share ${(theme.destination_median * 100).toFixed(1)}%`}
            >
              <div className="grid gap-4 md:grid-cols-[auto_1fr] md:items-start">
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <Badge tone={theme.market_gap ? "dawn" : "neutral"}>
                    {theme.market_gap ? "market gap" : "localised"}
                  </Badge>
                  <span className="text-forest-700">
                    <span className="font-semibold">{theme.affected_properties}</span>
                    <span className="text-forest-500"> / {theme.cluster_size}</span>{" "}
                    properties affected
                  </span>
                  <span className="text-forest-700">
                    <span className="font-semibold">{theme.total_negatives}</span>{" "}
                    total negatives
                  </span>
                  <span className="flex items-center gap-2 text-xs text-forest-500">
                    6-mo trend
                    <Sparkline
                      points={theme.trend.map((t) => t.negative_share)}
                      ariaLabel={`${theme.aspect} negative share trend`}
                    />
                  </span>
                </div>
              </div>

              <div className="mt-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-forest-500">
                  Evidence
                </p>
                <ul className="space-y-2">
                  {theme.quotes.map((q, i) => (
                    <li
                      key={i}
                      className="rounded-lg bg-mist-100 px-3 py-2 text-sm"
                    >
                      <p className="text-forest-800">“{q.span}”</p>
                      <p className="mt-1 text-xs text-forest-500">
                        {q.property_id} · {q.platform} · {q.date}
                        {q.source_url ? (
                          <>
                            {" · "}
                            <a
                              href={q.source_url}
                              className="text-forest-600 underline"
                              target="_blank"
                              rel="noreferrer"
                            >
                              source
                            </a>
                          </>
                        ) : (
                          " · source URL unavailable"
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          ))}
        </div>
      </LoadState>
    </div>
  );
}
