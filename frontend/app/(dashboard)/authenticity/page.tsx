"use client";

import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { api, type AuthenticityResponse } from "@/lib/api";

export default function AuthenticityPage() {
  const { status, data, reload } = useLiveData<AuthenticityResponse>(
    () => api.authenticity(),
    { isEmpty: (d) => d.rankings.length === 0 && d.flagged_reviews.length === 0 },
  );
  const badge = liveBadgeProps(status);

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F9"
        title="Authenticity Filter"
        description="Flags reviews that show suspicious signals — a daily burst (above the 28-day rolling mean + 3 SD), near-duplicate text (cosine ≥ 0.9) and single-review authors — and computes a 0–1 suspicion score. These are suspicious signals, not confirmed fakes. The adjusted view re-ranks the cluster excluding reviews with suspicion ≥ 0.7 and shows original vs adjusted ranks side by side."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <LoadState status={status} onRetry={reload}>
      {data && (<>
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatTile
          label="Reviews analysed"
          value={data.total_reviews}
          hint="across the cluster"
        />
        <StatTile
          label="Excluded (suspicion ≥ 0.7)"
          value={data.excluded_count}
          trend="down"
          hint="from the adjusted ranking"
        />
        <StatTile
          label="Near-duplicate threshold"
          value={data.near_duplicate_threshold.toFixed(2)}
          hint="cosine similarity"
        />
      </div>

      <Card
        title="Original vs authenticity-adjusted rankings"
        subtitle="Rankings recomputed after excluding high-suspicion reviews"
        className="mb-6"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-forest-600">
                <th className="py-2">Property</th>
                <th className="py-2">Original rank</th>
                <th className="py-2">Adjusted rank</th>
                <th className="py-2">Change</th>
              </tr>
            </thead>
            <tbody>
              {data.rankings.map((r) => (
                <tr key={r.property_id} className="border-t border-mist-200">
                  <td className="py-2 font-medium text-forest-800">
                    {r.property_name}
                  </td>
                  <td className="py-2">
                    #{r.original_rank} ({r.original_mean.toFixed(2)})
                  </td>
                  <td className="py-2">
                    #{r.adjusted_rank} ({r.adjusted_mean.toFixed(2)})
                  </td>
                  <td className="py-2">
                    {r.rank_delta === 0 ? (
                      <span className="text-forest-500">—</span>
                    ) : r.rank_delta > 0 ? (
                      <Badge tone="forest">▲ {r.rank_delta}</Badge>
                    ) : (
                      <Badge tone="dawn">▼ {Math.abs(r.rank_delta)}</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Flagged reviews"
        subtitle="Labelled 'suspicious signals' — never confirmed fake"
      >
        <ul className="space-y-3">
          {data.flagged_reviews.slice(0, 12).map((r) => (
            <li
              key={r.review_id}
              className="rounded-xl border border-mist-200 bg-mist-50 p-3"
            >
              <div className="flex flex-wrap items-center gap-2 text-xs text-forest-600">
                <span className="font-medium text-forest-800">
                  {r.property_name}
                </span>
                <span>· {r.platform}</span>
                <span>· {r.date}</span>
                <span>· ★{r.rating}</span>
                <Badge tone="dawn">suspicion {r.suspicion.toFixed(2)}</Badge>
              </div>
              <p className="mt-2 text-sm text-forest-800">“{r.text}”</p>
              <div className="mt-2 flex flex-wrap gap-1 text-xs">
                {r.burst && <Badge tone="neutral">burst</Badge>}
                {r.near_duplicate && <Badge tone="neutral">near-duplicate</Badge>}
                {r.single_review_author && (
                  <Badge tone="neutral">single-review author</Badge>
                )}
                <Badge tone="pine">{r.label}</Badge>
              </div>
            </li>
          ))}
        </ul>
      </Card>
      </>)}
      </LoadState>
    </div>
  );
}
