"use client";

import { useEffect } from "react";
import { PageHeader, Card, Badge, StatTile } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { api, type BoardResponse, type BoardRow } from "@/lib/api";

const POLL_MS = 4000; // < 5s budget (Req 15.6)

function urgencyTone(urgency: string | undefined) {
  switch (urgency) {
    case "P1":
      return "dawn" as const;
    case "P2":
      return "pine" as const;
    default:
      return "neutral" as const;
  }
}

function countdown(hours: number) {
  if (hours <= 0) return "checked out";
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return `${h}h ${m}m`;
}

export default function CheckoutShieldPage() {
  const { status, data, reload } = useLiveData<BoardResponse>(
    () => api.board(),
    { isEmpty: (d) => (d.rows?.length ?? 0) === 0 },
  );
  const badge = liveBadgeProps(status);

  // Poll the live board on a <5s cadence (Req 15.6).
  useEffect(() => {
    const id = setInterval(reload, POLL_MS);
    return () => clearInterval(id);
  }, [reload]);

  const rows = data?.rows ?? [];
  const highRisk = rows.filter((r) => r.high_risk).length;
  const pinned = rows.filter((r) => r.pinned).length;

  return (
    <div>
      <PageHeader
        eyebrow="In-Stay Sentinel · F3"
        title="Checkout Shield"
        description="A live risk board of every in-house stay, sorted by risk. High-risk stays (≥ 0.6) are highlighted and alert managers; those with under 4 hours to checkout are pinned to the top so the team can recover the guest before they leave."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={badge.tone}>
              {status === "ready" ? "Live · auto-refresh 4s" : badge.label}
            </Badge>
          </div>
        }
      />

      <LoadState
        status={status}
        onRetry={reload}
        emptyTitle="No in-house stays"
        emptyBody="The backend is reachable but no stays are currently tracked. Seed demo stays to populate the Checkout Shield board."
      >
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="In-house stays" value={rows.length} hint="currently tracked" />
          <StatTile
            label="High risk (≥ 0.6)"
            value={highRisk}
            trend={highRisk > 0 ? "down" : "flat"}
            hint="managers notified"
          />
          <StatTile
            label="Pinned (< 4h to checkout)"
            value={pinned}
            trend={pinned > 0 ? "down" : "flat"}
            hint="recover before checkout"
          />
          <StatTile
            label="Risk threshold"
            value={data?.high_risk_threshold ?? 0.6}
            hint="highlight + alert"
          />
        </div>

        <div className="space-y-3">
          {rows.map((row) => (
            <RiskCard key={row.stay_id} row={row} />
          ))}
        </div>
      </LoadState>
    </div>
  );
}

function RiskCard({ row }: { row: BoardRow }) {
  const score = row.score ?? 0;
  const pct = Math.round(score * 100);
  const highlight = row.high_risk;
  return (
    <div
      className={`rounded-2xl border p-5 shadow-tile ${
        highlight
          ? "border-dawn-400 bg-dawn-400/10"
          : "border-mist-300 bg-mist-50"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-[200px]">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-forest-800">
              Room {row.room}
            </span>
            {row.pinned && <Badge tone="dawn">📌 pinned</Badge>}
            {highlight && !row.pinned && <Badge tone="dawn">high risk</Badge>}
          </div>
          <p className="mt-1 text-sm text-forest-600">
            Guest {row.guest_pseudonym} · checkout in{" "}
            <span className="font-medium">{countdown(row.hours_to_checkout)}</span>
          </p>
        </div>

        <div className="text-right">
          <div className="text-3xl font-semibold text-forest-800">
            {score.toFixed(2)}
          </div>
          <div className="mt-1 h-2 w-40 overflow-hidden rounded-full bg-mist-200">
            <div
              className={`h-full ${highlight ? "bg-dawn-500" : "bg-forest-500"}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-forest-500">risk score</p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-forest-500">
            Top open complaint
          </p>
          {row.top_open_complaint ? (
            <div className="mt-1 text-sm text-forest-800">
              <div className="flex items-center gap-2">
                <Badge tone={urgencyTone(row.top_open_complaint.urgency)}>
                  {row.top_open_complaint.urgency}
                </Badge>
                <span className="font-medium">
                  {row.top_open_complaint.issue_type}
                </span>
                <span className="text-forest-500">
                  → {row.responsible_department}
                </span>
              </div>
              <p className="mt-1 text-forest-600">
                “{row.top_open_complaint.text}”
              </p>
              {row.sop_action && (
                <p className="mt-1 text-xs text-forest-500">
                  SOP: {row.sop_action}
                </p>
              )}
            </div>
          ) : (
            <p className="mt-1 text-sm text-forest-500">No open complaints.</p>
          )}
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-forest-500">
            Top contributing factors
          </p>
          <ul className="mt-1 space-y-1 text-sm text-forest-700">
            {(row.top_factors ?? []).length === 0 ? (
              <li className="text-forest-500">Low baseline risk.</li>
            ) : (
              row.top_factors.map((f, i) => (
                <li key={i} className="flex items-center justify-between gap-2">
                  <span>{f.label}</span>
                  <span className="text-xs text-forest-500">
                    +{f.contribution.toFixed(2)}
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
