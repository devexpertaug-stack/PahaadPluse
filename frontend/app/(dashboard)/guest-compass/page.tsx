"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import {
  api,
  type GuestCompassStay,
  type GuestCompassMetrics,
  type Recommendations,
  type RecommendationCard,
} from "@/lib/api";

function categoryTone(category: string) {
  switch (category) {
    case "food":
      return "dawn" as const;
    case "spa":
      return "pine" as const;
    case "rooms":
      return "forest" as const;
    default:
      return "neutral" as const;
  }
}

export default function GuestCompassPage() {
  const staysState = useLiveData<GuestCompassStay[]>(
    async () => (await api.guestCompassStays()).stays,
    { isEmpty: (d) => d.length === 0 },
  );
  const metricsState = useLiveData<GuestCompassMetrics>(() =>
    api.guestCompassMetrics(),
  );
  const [selected, setSelected] = useState<string>("");
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [busy, setBusy] = useState(false);
  const [revenueInput, setRevenueInput] = useState<Record<string, string>>({});

  const stays = staysState.data ?? [];
  const metrics = metricsState.data;
  const badge = liveBadgeProps(staysState.status);

  // Default-select the first stay once the live list loads.
  const firstStayId = staysState.data?.[0]?.id ?? null;
  useEffect(() => {
    if (!selected && firstStayId) {
      setSelected(firstStayId);
    }
  }, [firstStayId, selected]);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    api
      .guestRecommendations(selected)
      .then((r) => active && setRecs(r))
      .catch(() => active && setRecs(null));
    return () => {
      active = false;
    };
  }, [selected]);

  async function record(card: RecommendationCard, accepted: boolean) {
    setBusy(true);
    try {
      const revenue = accepted
        ? Number(revenueInput[card.item_id] ?? card.price_inr) || card.price_inr
        : 0;
      const res = await api.guestOutcome(selected, {
        item_id: card.item_id,
        accepted,
        revenue_inr: revenue,
      });
      setRecs(res.recommendations);
      metricsState.reload();
    } catch {
      /* surfaced via the live error state on reload */
    } finally {
      setBusy(false);
    }
  }

  const activeStay = stays.find((s) => s.id === selected);

  return (
    <div>
      <PageHeader
        eyebrow="Guest Compass"
        title="Guest Compass"
        description="Contextual-bandit upsell recommendations for a Stay. Cold-start segments drive the first offers; the policy learns from accept/decline. Aspects where this property trails the cluster median are down-weighted, and upsells are suppressed while a Stay has an open P1/P2 complaint."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      {metrics && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Uptake rate"
            value={`${Math.round(metrics.uptake_rate * 100)}%`}
            trend="up"
            hint={`${metrics.accepted}/${metrics.offers} offers accepted`}
          />
          <StatTile
            label="Ancillary revenue"
            value={`₹${metrics.ancillary_revenue_inr.toLocaleString("en-IN")}`}
            hint="this week"
          />
          <StatTile
            label="Revenue / guest / week"
            value={`₹${metrics.revenue_per_guest_per_week.toLocaleString("en-IN")}`}
            hint={`${metrics.guests_this_week} guests`}
          />
          <StatTile label="Offers made" value={metrics.offers} hint="all stays" />
        </div>
      )}

      <LoadState
        status={staysState.status}
        onRetry={staysState.reload}
        emptyTitle="No active stays"
        emptyBody="The backend is reachable but there are no stays to recommend upsells for. Seed demo stays to populate Guest Compass."
      >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.6fr]">
        <Card title="Stays" subtitle="Open a Stay to see front-desk offers">
          <ul className="space-y-2">
            {stays.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => setSelected(s.id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left ${
                    s.id === selected
                      ? "border-forest-400 bg-forest-100"
                      : "border-mist-300 bg-mist-50 hover:bg-mist-100"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-forest-800">
                      {s.label}
                    </span>
                    {s.has_open_p1_p2 && <Badge tone="dawn">P1/P2 open</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-forest-500">
                    {s.purpose} · {s.party}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          title={activeStay ? `Offers · ${activeStay.label}` : "Recommendation cards"}
          subtitle={
            !recs
              ? "Loading offers…"
              : recs.suppressed
                ? "Upsell suppressed"
                : recs.cold_start
                  ? `Cold-start segment: ${recs.segment ?? ""}`
                  : "Learned policy"
          }
        >
          {!recs ? (
            <p className="text-sm text-forest-600">Loading recommendations…</p>
          ) : recs.suppressed ? (
            <div className="rounded-xl border border-dawn-400/40 bg-dawn-400/10 p-4 text-sm text-forest-800">
              <p className="font-medium">Upsell cards suppressed</p>
              <p className="mt-1 text-forest-600">
                {recs.reason ??
                  "This Stay has an open P1/P2 complaint — resolve it before offering extras."}
              </p>
            </div>
          ) : (
            <>
              {recs.market_weak_aspects && recs.market_weak_aspects.length > 0 && (
                <p className="mb-3 text-xs text-forest-500">
                  Market-weak aspects down-weighted:{" "}
                  {recs.market_weak_aspects.join(", ")}
                </p>
              )}
              <ul className="space-y-3">
                {recs.cards.map((card) => (
                  <li
                    key={card.item_id}
                    className="rounded-xl border border-mist-300 bg-mist-50 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge tone={categoryTone(card.category)}>
                            {card.category}
                          </Badge>
                          <span className="text-sm font-semibold text-forest-800">
                            {card.name}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-forest-600">{card.reason}</p>
                        <p className="mt-1 text-xs text-forest-500">
                          ₹{card.price_inr.toLocaleString("en-IN")} · score{" "}
                          {card.score.toFixed(2)}
                          {card.market_down_weighted && " · market down-weighted"}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <input
                        type="number"
                        aria-label={`${card.name} revenue`}
                        placeholder={`₹${card.price_inr}`}
                        value={revenueInput[card.item_id] ?? ""}
                        onChange={(e) =>
                          setRevenueInput((prev) => ({
                            ...prev,
                            [card.item_id]: e.target.value,
                          }))
                        }
                        className="w-28 rounded-lg border border-mist-300 px-2 py-1 text-sm"
                      />
                      <Button
                        size="sm"
                        onClick={() => record(card, true)}
                        disabled={busy}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => record(card, false)}
                        disabled={busy}
                      >
                        Decline
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      </div>
      </LoadState>
    </div>
  );
}
