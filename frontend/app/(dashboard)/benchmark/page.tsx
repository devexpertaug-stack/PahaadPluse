"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, Card, Badge } from "@/components/ui";
import { api, type BenchmarkResponse, type BenchmarkSystem } from "@/lib/api";
import analytics from "@/lib/analyticsSnapshot.json";

const BENCHMARK = analytics.benchmark as unknown as BenchmarkResponse;
const LABELS = ["positive", "neutral", "negative"] as const;

function Metric({
  value,
  ci,
}: {
  value: number;
  ci: [number, number];
}) {
  return (
    <span className="tabular-nums">
      <span className="font-semibold text-forest-800">{value.toFixed(3)}</span>{" "}
      <span className="text-xs text-forest-500">
        [{ci[0].toFixed(3)}, {ci[1].toFixed(3)}]
      </span>
    </span>
  );
}

export default function BenchmarkPage() {
  const [data, setData] = useState<BenchmarkResponse>(BENCHMARK);
  const [live, setLive] = useState(false);
  const [system, setSystem] = useState<string>(BENCHMARK.systems[0]?.name ?? "");

  useEffect(() => {
    let active = true;
    api
      .benchmark()
      .then((b) => {
        if (active) {
          setData(b);
          setSystem(b.systems[0]?.name ?? "");
          setLive(true);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const selected: BenchmarkSystem | undefined = useMemo(
    () => data.systems.find((s) => s.name === system) ?? data.systems[0],
    [data, system],
  );

  const aspectKeys = selected
    ? Object.keys(selected.aspect_confusion).sort()
    : [];

  return (
    <div>
      <PageHeader
        eyebrow="Bhasha Concierge · F12"
        title="Hinglish Accuracy Benchmark"
        description={`Macro-F1 with 95% bootstrap CIs for the Sentiment_Engine, a generic off-the-shelf tool and a plain-LLM zero-shot baseline on ${data.test_set_size} held-out reviews. Idempotent for seed ${data.seed}.`}
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

      <Card
        title="Results by system"
        subtitle="Macro-F1 [95% bootstrap CI]"
        className="mb-6"
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-forest-50 text-left text-forest-700">
                <th className="px-4 py-3 font-semibold">System</th>
                <th className="px-4 py-3 font-semibold">Overall sentiment</th>
                <th className="px-4 py-3 font-semibold">Aspect detection</th>
                <th className="px-4 py-3 font-semibold">Aspect sentiment</th>
              </tr>
            </thead>
            <tbody>
              {data.systems.map((s) => (
                <tr
                  key={s.name}
                  className="border-t border-mist-200 hover:bg-mist-100"
                >
                  <td className="px-4 py-3 font-medium text-forest-800">
                    {s.name}
                  </td>
                  <td className="px-4 py-3">
                    <Metric
                      value={s.overall_sentiment.macro_f1}
                      ci={s.overall_sentiment.ci_95}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Metric
                      value={s.aspect_detection.macro_f1}
                      ci={s.aspect_detection.ci_95}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Metric
                      value={s.aspect_sentiment.macro_f1}
                      ci={s.aspect_sentiment.ci_95}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Per-aspect confusion matrix"
        subtitle="Aspect-sentiment predictions vs gold labels"
      >
        <div className="mb-4 flex flex-wrap gap-2">
          {data.systems.map((s) => (
            <button
              key={s.name}
              type="button"
              onClick={() => setSystem(s.name)}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                system === s.name
                  ? "border-forest-600 bg-forest-100 text-forest-800"
                  : "border-mist-300 bg-mist-50 text-forest-600 hover:bg-mist-100"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {selected &&
            aspectKeys.map((aspect) => {
              const matrix = selected.aspect_confusion[aspect].matrix;
              const support = selected.aspect_confusion[aspect].support.n;
              const max = Math.max(
                1,
                ...LABELS.flatMap((g) => LABELS.map((p) => matrix[g][p])),
              );
              return (
                <div
                  key={aspect}
                  className="rounded-xl border border-mist-300 bg-mist-50 p-3"
                >
                  <p className="mb-2 text-sm font-semibold text-forest-800">
                    {aspect.replace(/_/g, " ")}{" "}
                    <span className="text-xs font-normal text-forest-500">
                      (n={support})
                    </span>
                  </p>
                  <table className="w-full border-collapse text-center text-xs">
                    <thead>
                      <tr className="text-forest-500">
                        <th className="p-1" />
                        {LABELS.map((p) => (
                          <th key={p} className="p-1 font-medium">
                            {p.slice(0, 3)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {LABELS.map((g) => (
                        <tr key={g}>
                          <td className="p-1 text-left font-medium text-forest-500">
                            {g.slice(0, 3)}
                          </td>
                          {LABELS.map((p) => {
                            const v = matrix[g][p];
                            const intensity = v / max;
                            return (
                              <td
                                key={p}
                                className="p-1 tabular-nums text-forest-800"
                                style={{
                                  background: `rgba(63, 129, 80, ${0.12 + intensity * 0.5})`,
                                }}
                              >
                                {v}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
        </div>
        <p className="mt-3 text-xs text-forest-500">
          Rows = gold label, columns = predicted. The test set is disjoint from
          the Sentiment_Engine tuning vocabulary (Req 16.6).
        </p>
      </Card>
    </div>
  );
}
