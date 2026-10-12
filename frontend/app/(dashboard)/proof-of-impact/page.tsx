"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import { MiniTrend } from "@/components/common/MiniTrend";
import { api, type ImpactResult, ASPECTS } from "@/lib/api";
import snapshot from "@/lib/impactSnapshot.json";

const RESULTS = snapshot.results as unknown as ImpactResult[];

export default function ProofOfImpactPage() {
  const [results, setResults] = useState<ImpactResult[]>(RESULTS);
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    aspect: "Food",
    description: "",
    date: "2024-04-01",
  });

  function load() {
    api
      .impact()
      .then((res) => {
        if (res.results.length) {
          setResults(res.results);
          setLive(true);
        }
      })
      .catch(() => {});
  }

  useEffect(load, []);

  async function logIntervention() {
    setBusy(true);
    try {
      await api.logIntervention({
        property_id: "mus-pineview",
        aspect: form.aspect,
        description: form.description || `Intervention on ${form.aspect}`,
        date: form.date,
      });
      load();
    } catch {
      /* offline */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F10"
        title="Proof of Impact"
        description="Log an operational intervention; once there are 30+ days of post-intervention reviews we estimate a difference-in-differences effect on the aspect score using the other cluster properties as a control, with a 90% confidence interval and a parallel-trends check."
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

      <Card
        title="Log an intervention"
        subtitle="Date · Aspect · description for the Home Property"
        className="mb-6"
      >
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="mb-1 block text-xs text-forest-500">Aspect</span>
            <select
              aria-label="Aspect"
              value={form.aspect}
              onChange={(e) => setForm({ ...form, aspect: e.target.value })}
              className="rounded-lg border border-mist-300 px-2 py-1"
            >
              {ASPECTS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs text-forest-500">Date</span>
            <input
              type="date"
              aria-label="Date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="rounded-lg border border-mist-300 px-2 py-1"
            />
          </label>
          <label className="flex-1 text-sm">
            <span className="mb-1 block text-xs text-forest-500">Description</span>
            <input
              aria-label="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="e.g. Replaced breakfast vendor"
              className="w-full rounded-lg border border-mist-300 px-2 py-1"
            />
          </label>
          <Button onClick={logIntervention} disabled={busy}>
            Log + estimate
          </Button>
        </div>
      </Card>

      <div className="space-y-6">
        {results.map((r) => (
          <Card
            key={r.intervention_id}
            title={`${r.aspect} intervention · ${r.intervention_date}`}
            subtitle={`${r.post_days} days of post-intervention data`}
          >
            {!r.sufficient_post_data ? (
              <p className="rounded-lg bg-dawn-400/10 p-3 text-sm text-forest-700">
                {r.message}
              </p>
            ) : (
              <>
                <div className="mb-4 grid gap-4 sm:grid-cols-3">
                  <StatTile
                    label="DiD effect"
                    value={`${r.effect! >= 0 ? "+" : ""}${r.effect!.toFixed(2)}`}
                    trend={r.effect! >= 0 ? "up" : "down"}
                    hint="aspect score points"
                  />
                  <StatTile
                    label="90% CI"
                    value={`[${r.ci_lower!.toFixed(2)}, ${r.ci_upper!.toFixed(2)}]`}
                    hint="difference-in-differences"
                  />
                  <StatTile
                    label="Parallel trends"
                    value={r.parallel_trends_warning ? "⚠ differ" : "OK"}
                    trend={r.parallel_trends_warning ? "down" : "flat"}
                    hint={
                      r.parallel_trends_pvalue != null
                        ? `p=${r.parallel_trends_pvalue.toFixed(2)}`
                        : ""
                    }
                  />
                </div>

                {r.parallel_trends_warning && (
                  <p className="mb-4 rounded-lg border border-dawn-400/40 bg-dawn-400/10 p-3 text-sm text-forest-800">
                    Parallel-trends warning: pre-period trends for the home and
                    control groups differ significantly (p &lt; 0.05). Interpret
                    the DiD effect with caution.
                  </p>
                )}

                <p className="mb-2 text-sm font-medium text-forest-700">
                  Pre/post aspect score — Home vs control
                </p>
                <MiniTrend
                  yMin={1}
                  yMax={5}
                  series={[
                    {
                      label: "Home (Pine View Inn)",
                      color: "#275233",
                      points: r.home_trend.map((p) => ({ x: p.week, y: p.score })),
                    },
                    {
                      label: "Cluster control",
                      color: "#dca24c",
                      points: r.control_trend.map((p) => ({
                        x: p.week,
                        y: p.score,
                      })),
                    },
                  ]}
                />
              </>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
