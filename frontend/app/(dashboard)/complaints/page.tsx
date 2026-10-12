"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import {
  api,
  type ComplaintView,
  type SentinelMetrics,
} from "@/lib/api";

function urgencyTone(u: string | null) {
  if (u === "P1") return "dawn" as const;
  if (u === "P2") return "pine" as const;
  return "neutral" as const;
}

function stateTone(s: string) {
  if (s === "resolved") return "forest" as const;
  if (s === "escalated") return "dawn" as const;
  return "neutral" as const;
}

export default function ComplaintsPage() {
  const complaintsState = useLiveData<ComplaintView[]>(
    async () => (await api.complaints()).complaints,
    { isEmpty: (d) => d.length === 0 },
  );
  const metricsState = useLiveData<SentinelMetrics>(() =>
    api.sentinelMetrics(),
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const complaints = complaintsState.data ?? [];
  const metrics = metricsState.data;
  const badge = liveBadgeProps(complaintsState.status);

  function refresh() {
    complaintsState.reload();
    metricsState.reload();
  }

  // Default-select the first complaint once the live queue loads.
  const firstComplaintId = complaintsState.data?.[0]?.id ?? null;
  useEffect(() => {
    if (selected === null && firstComplaintId) {
      setSelected(firstComplaintId);
    }
  }, [firstComplaintId, selected]);

  const active = complaints.find((c) => c.id === selected) ?? null;

  async function triggerWhatsappDemo() {
    setBusy(true);
    try {
      const res = await api.demoWhatsapp({
        from_number: "+919800000309",
        body: "room mein geyser kaam nahi kar raha",
        language: "hi-Latn",
      });
      setSelected(res.complaint.id);
      refresh();
    } catch {
      /* offline demo: no-op */
    } finally {
      setBusy(false);
    }
  }

  async function resolve(id: string) {
    setBusy(true);
    try {
      await api.resolveComplaint(id, "Resolved by staff from the complaints queue.");
      refresh();
    } catch {
      /* offline */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="In-Stay Sentinel"
        title="Complaints"
        description="Multi-channel complaint intake, triage to the right department with the matching SOP, resolution tracking and recurrence detection. The weekly operations metrics sit on top."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={badge.tone}>{badge.label}</Badge>
            <Button size="sm" onClick={triggerWhatsappDemo} disabled={busy}>
              Simulate WhatsApp complaint
            </Button>
          </div>
        }
      />

      {metrics && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Complaint → department"
            value={`${metrics.avg_complaint_to_department_seconds.toFixed(1)}s`}
            hint="avg time to assign"
          />
          <StatTile
            label="In-stay resolution rate"
            value={`${Math.round(metrics.in_stay_resolution_rate * 100)}%`}
            trend="up"
            hint="resolved before checkout"
          />
          <StatTile
            label="Repeat complaints / week"
            value={metrics.repeat_complaints_this_week}
            trend={metrics.repeat_complaints_this_week > 0 ? "down" : "flat"}
            hint="recurrence this week"
          />
          <StatTile
            label="Open complaints"
            value={metrics.open_complaints}
            hint={`${metrics.resolved_complaints} resolved`}
          />
        </div>
      )}

      <LoadState
        status={complaintsState.status}
        onRetry={refresh}
        emptyTitle="No complaints yet"
        emptyBody="The backend is reachable but the complaint queue is empty. Simulate a WhatsApp complaint above to see triage in action."
      >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.3fr]">
        <Card title="Queue" subtitle="Newest first, across all five channels">
          <ul className="space-y-2">
            {complaints.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSelected(c.id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left ${
                    c.id === selected
                      ? "border-forest-400 bg-forest-100"
                      : "border-mist-300 bg-mist-50 hover:bg-mist-100"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-forest-800">
                      {c.room ? `Room ${c.room}` : "No room"} · {c.issue_type}
                    </span>
                    <div className="flex items-center gap-1">
                      {c.is_recurrence && <Badge tone="dawn">recurring</Badge>}
                      <Badge tone={urgencyTone(c.urgency)}>{c.urgency}</Badge>
                    </div>
                  </div>
                  <p className="mt-1 truncate text-xs text-forest-500">
                    {c.channel} · {c.department} · {c.state}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          title={active ? `Triage · ${active.id}` : "Select a complaint"}
          subtitle="Department, urgency, SOP steps and resolution"
        >
          {!active ? (
            <p className="text-sm text-forest-600">
              Select a complaint from the queue to see its triage and SOP.
            </p>
          ) : (
            <ComplaintDetail
              complaint={active}
              busy={busy}
              onResolve={() => resolve(active.id)}
            />
          )}
        </Card>
      </div>
      </LoadState>
    </div>
  );
}

function ComplaintDetail({
  complaint: c,
  busy,
  onResolve,
}: {
  complaint: ComplaintView;
  busy: boolean;
  onResolve: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={urgencyTone(c.urgency)}>{c.urgency}</Badge>
        <Badge tone="neutral">{c.department}</Badge>
        <Badge tone={stateTone(c.state)}>{c.state}</Badge>
        {c.is_recurrence && <Badge tone="dawn">recurrence of {c.recurrence_of}</Badge>}
        {c.escalated && <Badge tone="dawn">escalated to managers</Badge>}
        {c.requires_manual_assignment && (
          <Badge tone="dawn">manual assignment</Badge>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-forest-500">
          Complaint
        </p>
        <p className="mt-1 text-sm text-forest-800">“{c.text}”</p>
        <p className="mt-1 text-xs text-forest-500">
          {c.channel} · {c.language} · created {new Date(c.created_at).toLocaleString()}
        </p>
        {c.transcript && (
          <div className="mt-2 rounded-lg bg-mist-100 px-3 py-2 text-xs text-forest-600">
            <p>Voice transcript: {c.transcript}</p>
            {c.transcript_translation_en && (
              <p className="mt-1">EN: {c.transcript_translation_en}</p>
            )}
            {c.transcription_confidence != null && (
              <p className="mt-1">
                confidence {c.transcription_confidence.toFixed(2)}
                {c.flagged_for_staff && " · flagged for staff"}
              </p>
            )}
          </div>
        )}
      </div>

      {c.original_predicted_department &&
        c.original_predicted_department !== c.department && (
          <p className="text-xs text-forest-500">
            Original prediction: {c.original_predicted_department} (confidence{" "}
            {c.department_confidence?.toFixed(2)})
          </p>
        )}

      {c.sop && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-forest-500">
            SOP · {c.sop.department} · target {c.sop.target_resolution_minutes} min
          </p>
          <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm text-forest-700">
            {c.sop.corrective_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {c.reassignments.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-forest-500">
            Reassignments
          </p>
          <ul className="mt-1 space-y-1 text-xs text-forest-600">
            {c.reassignments.map((r, i) => (
              <li key={i}>
                {r.from} → {r.to} · {r.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center gap-3">
        {c.state !== "resolved" ? (
          <Button onClick={onResolve} disabled={busy}>
            Mark resolved
          </Button>
        ) : (
          <p className="text-sm text-forest-600">
            Resolved {c.resolved_at ? new Date(c.resolved_at).toLocaleString() : ""}
            {c.resolution_note ? ` · ${c.resolution_note}` : ""}
          </p>
        )}
      </div>
    </div>
  );
}
