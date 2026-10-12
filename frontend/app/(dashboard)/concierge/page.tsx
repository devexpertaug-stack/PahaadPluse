"use client";

import { useEffect, useRef, useState } from "react";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import {
  api,
  type ConciergeResult,
  type ConciergeMetrics,
  type PropertyFactView,
} from "@/lib/api";

interface Turn {
  question: string;
  result: ConciergeResult;
}

const LANG_LABEL: Record<string, string> = {
  en: "English",
  hi: "हिन्दी",
  bn: "বাংলা",
  ta: "தமிழ்",
  fr: "Français",
};

const SAMPLE_QUESTIONS = [
  "What time is breakfast?",
  "नाश्ता कितने बजे है?",
  "Où est le petit déjeuner?",
  "প্রাতরাশ কখন?",
  "Is there a swimming pool?",
  "the room is dirty and the geyser is not working",
];

export default function ConciergePage() {
  const factsState = useLiveData<PropertyFactView[]>(
    async () => (await api.conciergeFacts()).facts,
    { isEmpty: (d) => d.length === 0 },
  );
  const metricsState = useLiveData<ConciergeMetrics>(() =>
    api.conciergeMetrics(),
  );
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [factEdits, setFactEdits] = useState<Record<string, string>>({});
  const endRef = useRef<HTMLDivElement>(null);

  const facts = factsState.data ?? [];
  const metrics = metricsState.data;
  const badge = liveBadgeProps(factsState.status);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send(message: string) {
    if (!message.trim()) return;
    setBusy(true);
    setChatError(null);
    try {
      const res = await api.conciergeMessage(message);
      setTurns((prev) => [...prev, { question: message, result: res.result }]);
      metricsState.reload();
    } catch {
      // No fabricated offline answer: surface honestly that the live concierge
      // backend is unreachable rather than inventing a grounded reply.
      setChatError(
        "Could not reach the concierge backend. Start the API and try again — answers are generated live, not from a snapshot.",
      );
    } finally {
      setInput("");
      setBusy(false);
    }
  }

  async function saveFact(fact: PropertyFactView) {
    const text = factEdits[fact.id];
    if (!text) return;
    setBusy(true);
    try {
      await api.updateFact(fact.id, text);
      factsState.reload();
      setFactEdits((prev) => ({ ...prev, [fact.id]: "" }));
    } catch {
      setChatError("Could not save the fact — the backend is unreachable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Bhasha Concierge"
        title="Bhasha Concierge"
        description="A multilingual guest assistant (Hindi, English, Bengali, Tamil, French). Every answer is grounded in versioned Property_Facts with the fact ids logged. Low-confidence queries hand off to the front desk; complaint messages open a Sentinel complaint on the concierge channel."
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      {metrics && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <StatTile
            label="Resolved without staff"
            value={`${Math.round(metrics.resolved_without_staff_rate * 100)}%`}
            trend="up"
            hint="this week"
          />
          <StatTile
            label="Queries answered"
            value={metrics.resolved_without_staff}
            hint={`${metrics.total_queries} total`}
          />
          <StatTile
            label="Handed off"
            value={metrics.handed_off}
            hint="to front desk"
          />
        </div>
      )}

      {chatError && (
        <div className="mb-4 rounded-xl border border-dawn-400/50 bg-dawn-400/10 px-4 py-2 text-sm text-forest-800">
          {chatError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card title="Conversation" subtitle="Ask in any supported language">
          <div className="mb-3 flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => send(q)}
                disabled={busy}
                className="rounded-full border border-mist-300 bg-mist-100 px-3 py-1 text-xs text-forest-700 hover:bg-mist-200"
              >
                {q}
              </button>
            ))}
          </div>

          <div className="max-h-[26rem] space-y-3 overflow-y-auto rounded-xl bg-mist-100 p-3">
            {turns.length === 0 && (
              <p className="text-sm text-forest-500">
                Send a message or tap a sample question to start.
              </p>
            )}
            {turns.map((t, i) => (
              <div key={i} className="space-y-1">
                <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-forest-700 px-3 py-2 text-sm text-mist-50">
                  {t.question}
                </div>
                <div className="w-fit max-w-[90%] rounded-2xl rounded-bl-sm border border-mist-300 bg-mist-50 px-3 py-2 text-sm text-forest-800">
                  <div className="mb-1 flex flex-wrap items-center gap-1">
                    <Badge tone="neutral">
                      {LANG_LABEL[t.result.language] ?? t.result.language}
                    </Badge>
                    {t.result.is_complaint && (
                      <Badge tone="dawn">
                        complaint → Sentinel {t.result.complaint_id}
                      </Badge>
                    )}
                    {t.result.handed_off && (
                      <Badge tone="dawn">handed off</Badge>
                    )}
                    {!t.result.handed_off && !t.result.is_complaint && (
                      <Badge tone="forest">
                        conf {t.result.confidence.toFixed(2)}
                      </Badge>
                    )}
                  </div>
                  <p>
                    {t.result.is_complaint
                      ? "Thanks — I’ve logged this with our team as a complaint."
                      : t.result.answer}
                  </p>
                  {t.result.fact_ids.length > 0 && (
                    <p className="mt-1 text-xs text-forest-500">
                      Grounded in: {t.result.fact_ids.join(", ")}
                      {t.result.template_generated && " · template-generated"}
                    </p>
                  )}
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <form
            className="mt-3 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              aria-label="Message"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a guest question…"
              className="flex-1 rounded-xl border border-mist-300 px-3 py-2 text-sm"
            />
            <Button type="submit" disabled={busy}>
              Send
            </Button>
          </form>
        </Card>

        <Card
          title="Property Facts"
          subtitle="Versioned grounding source — edits reflect in answers within 5 minutes"
        >
          <LoadState
            status={factsState.status}
            onRetry={factsState.reload}
            emptyTitle="No property facts"
            emptyBody="The backend is reachable but has no grounding facts yet."
          >
          <ul className="space-y-3">
            {facts.map((f) => (
              <li
                key={f.id}
                className="rounded-xl border border-mist-200 bg-mist-50 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-forest-800">
                    {f.topic}
                  </span>
                  <Badge tone="neutral">v{f.version}</Badge>
                </div>
                <p className="mt-1 text-sm text-forest-600">{f.text}</p>
                <div className="mt-2 flex gap-2">
                  <input
                    aria-label={`Edit ${f.topic}`}
                    value={factEdits[f.id] ?? ""}
                    onChange={(e) =>
                      setFactEdits((prev) => ({
                        ...prev,
                        [f.id]: e.target.value,
                      }))
                    }
                    placeholder="New fact text…"
                    className="flex-1 rounded-lg border border-mist-300 px-2 py-1 text-xs"
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => saveFact(f)}
                    disabled={busy || !factEdits[f.id]}
                  >
                    Update
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          </LoadState>
        </Card>
      </div>
    </div>
  );
}
