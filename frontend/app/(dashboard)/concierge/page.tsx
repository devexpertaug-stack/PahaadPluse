"use client";

import { useEffect, useRef, useState } from "react";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import {
  api,
  type ConciergeResult,
  type ConciergeMetrics,
  type PropertyFactView,
} from "@/lib/api";
import snapshot from "@/lib/conciergeSnapshot.json";

const FACTS = snapshot.facts as unknown as PropertyFactView[];
const METRICS = snapshot.metrics as unknown as ConciergeMetrics;

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
  const [facts, setFacts] = useState<PropertyFactView[]>(FACTS);
  const [metrics, setMetrics] = useState<ConciergeMetrics>(METRICS);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [factEdits, setFactEdits] = useState<Record<string, string>>({});
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .conciergeFacts()
      .then((res) => {
        setFacts(res.facts);
        setLive(true);
      })
      .catch(() => {});
    api.conciergeMetrics().then(setMetrics).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send(message: string) {
    if (!message.trim()) return;
    setBusy(true);
    try {
      const res = await api.conciergeMessage(message);
      setTurns((prev) => [...prev, { question: message, result: res.result }]);
      api.conciergeMetrics().then(setMetrics).catch(() => {});
    } catch {
      // offline demo fallback: naive local grounding
      const fact = facts.find((f) =>
        message.toLowerCase().includes(f.topic.toLowerCase()),
      );
      const result: ConciergeResult = fact
        ? {
            language: "en",
            is_complaint: false,
            answer: fact.text,
            fact_ids: [fact.id],
            confidence: 0.9,
            handed_off: false,
            resolved_without_staff: true,
            template_generated: true,
            complaint_id: null,
          }
        : {
            language: "en",
            is_complaint: false,
            answer: "Our front-desk team will reply to you shortly.",
            fact_ids: [],
            confidence: 0.2,
            handed_off: true,
            resolved_without_staff: false,
            template_generated: false,
            complaint_id: null,
          };
      setTurns((prev) => [...prev, { question: message, result }]);
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
      const res = await api.updateFact(fact.id, text);
      setFacts((prev) => prev.map((f) => (f.id === fact.id ? res.fact : f)));
      setFactEdits((prev) => ({ ...prev, [fact.id]: "" }));
    } catch {
      /* offline */
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
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

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
        </Card>
      </div>
    </div>
  );
}
