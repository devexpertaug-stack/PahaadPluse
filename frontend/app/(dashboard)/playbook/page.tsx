"use client";

import { PageHeader, Card, Badge } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { api, type PlaybookResponse } from "@/lib/api";

export default function PlaybookPage() {
  const { status, data, reload } = useLiveData<PlaybookResponse>(() =>
    api.playbook(),
  );
  const badge = liveBadgeProps(status);

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F5"
        title="Steal-the-Winner Playbook"
        description={
          data
            ? `Where ${data.home_property_name} lags the cluster leader ${data.leader_property_name}, learn from the themes guests praise — with the exact counts behind every recommendation.`
            : "Where the home property lags the cluster leader, learn from the themes guests praise — with the exact counts behind every recommendation."
        }
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <LoadState status={status} onRetry={reload}>
        {data && data.lagging.length === 0 && (
          <Card title="No lagging aspects">
            <p className="text-sm text-forest-600">
              {data.message ??
                "The home property leads or matches the cluster on every aspect."}
            </p>
          </Card>
        )}

        <div className="space-y-6">
          {data?.lagging.map((lag) => (
            <Card
              key={lag.aspect}
              title={`${lag.aspect.replace(/_/g, " ")} is lagging`}
              subtitle={`Home 90% CI upper ${lag.home_upper.toFixed(2)} < leader lower ${lag.leader_lower.toFixed(2)}`}
            >
              <div className="mb-4 rounded-xl border border-forest-200 bg-forest-50/60 p-4">
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-sm font-semibold text-forest-800">
                    Suggested action
                  </span>
                  {lag.action_template_generated && (
                    <Badge tone="dawn">template-generated</Badge>
                  )}
                </div>
                <p className="text-sm leading-relaxed text-forest-700">
                  {lag.action_paragraph}
                </p>
              </div>

              {lag.themes.map((theme) => (
                <div key={theme.aspect} className="mb-4">
                  <div className="mb-2 flex flex-wrap items-center gap-3 text-sm">
                    <span className="font-medium text-forest-800">
                      Praised at {data.leader_property_name}
                    </span>
                    <Badge tone="forest">
                      {theme.leader_positive_count} positive mentions
                    </Badge>
                    <span className="text-forest-600">
                      Home: {theme.home_positive_count} positive ·{" "}
                      {theme.home_negative_count} negative
                    </span>
                  </div>
                  <ul className="space-y-2">
                    {theme.quotes.map((q, i) => (
                      <li
                        key={i}
                        className="rounded-lg bg-mist-100 px-3 py-2 text-sm"
                      >
                        <p className="text-forest-800">“{q.span}”</p>
                        <p className="mt-1 text-xs text-forest-500">
                          {q.platform} · {q.date} ·{" "}
                          <a
                            href={q.source_url}
                            className="text-forest-600 underline"
                            target="_blank"
                            rel="noreferrer"
                          >
                            source
                          </a>
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </Card>
          ))}
        </div>

        {data && data.undetermined.length > 0 && (
          <Card title="Lagging status undetermined" className="mt-6">
            <ul className="list-disc space-y-1 pl-5 text-sm text-forest-700">
              {data.undetermined.map((u) => (
                <li key={u.aspect}>
                  <span className="font-medium">
                    {u.aspect.replace(/_/g, " ")}
                  </span>{" "}
                  — {u.reason}
                </li>
              ))}
            </ul>
          </Card>
        )}
      </LoadState>
    </div>
  );
}
