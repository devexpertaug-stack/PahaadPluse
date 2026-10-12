"use client";

import { useState } from "react";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import { api, type BriefingResponse } from "@/lib/api";
import snapshot from "@/lib/briefingSnapshot.json";

const SNAPSHOT = snapshot as unknown as BriefingResponse;

export default function BriefingPage() {
  const [briefing, setBriefing] = useState<BriefingResponse>(SNAPSHOT);
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    try {
      const res = await api.briefing(["+919800000900"]);
      setBriefing(res.briefing);
      setLive(true);
    } catch {
      /* offline */
    } finally {
      setBusy(false);
    }
  }

  const m = briefing.metrics;

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F7"
        title="Owner's Weekly Hindi Voice Briefing"
        description="A weekly Hindi script covering the rating change, the top improving and declining aspect, new changepoints, the open P1/P2 complaint count and one recommended action. Every number comes from computed PahadPulse metrics; the LLM is used only for phrasing. The script is synthesised to a ≤60-second audio clip and delivered with the text to opted-in owners via the WhatsApp mock."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={live ? "forest" : "dawn"}>
              {live ? "Live from API" : "Sample snapshot"}
            </Badge>
            <Button size="sm" onClick={generate} disabled={busy}>
              Generate &amp; send
            </Button>
          </div>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Weekly rating"
          value={m.week_rating.toFixed(1)}
          trend={m.rating_change >= 0 ? "up" : "down"}
          hint={`${m.rating_change >= 0 ? "+" : ""}${m.rating_change.toFixed(1)} vs last week`}
        />
        <StatTile
          label="Top improving"
          value={m.top_improving_aspect ?? "—"}
          trend="up"
        />
        <StatTile
          label="Top declining"
          value={m.top_declining_aspect ?? "—"}
          trend="down"
        />
        <StatTile
          label="Open P1/P2"
          value={m.open_p1_p2}
          hint={`${m.new_changepoints} new changepoints`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Card
          title={`Hindi script · week of ${briefing.week_of}`}
          subtitle={
            briefing.template_generated
              ? "phrasing: template-generated"
              : "phrasing: LLM"
          }
        >
          <p className="whitespace-pre-wrap rounded-xl bg-mist-100 p-4 text-sm leading-relaxed text-forest-800">
            {briefing.script}
          </p>
          <p className="mt-3 text-xs text-forest-500">
            Recommended action: {m.recommended_action}
          </p>
        </Card>

        <Card title="Audio delivery" subtitle="TTS artifact + WhatsApp mock">
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-forest-600">Estimated duration</span>
              <Badge tone={briefing.within_cap ? "forest" : "dawn"}>
                {briefing.estimated_seconds}s / {briefing.max_seconds}s
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-forest-600">Audio engine</span>
              <Badge tone={briefing.audio_is_placeholder ? "dawn" : "forest"}>
                {briefing.audio_is_placeholder ? "placeholder" : "live TTS"}
              </Badge>
            </div>
            {briefing.audio_note && (
              <p className="rounded-lg bg-mist-100 p-2 text-xs text-forest-600">
                {briefing.audio_note}
              </p>
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-forest-500">
                Delivered to opted-in owners
              </p>
              <ul className="mt-1 space-y-1">
                {briefing.delivered_to.map((o) => (
                  <li key={o} className="text-forest-700">
                    🔊 {o}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
