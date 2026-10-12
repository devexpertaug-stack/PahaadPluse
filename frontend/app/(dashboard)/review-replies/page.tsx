"use client";

import { useState } from "react";
import { PageHeader, Card, Badge, Button } from "@/components/ui";
import { api, type ReplyDraft, ASPECTS } from "@/lib/api";

const SAMPLE_REVIEWS = [
  {
    review_id: "rev-food-en",
    property_id: "mus-pineview",
    text: "the food was cold and the breakfast variety was very limited",
    detected_language: "en",
    negative_aspects: ["Food"],
  },
  {
    review_id: "rev-room-hi",
    property_id: "mus-pineview",
    text: "कमरा ठंडा और छोटा था",
    detected_language: "hi",
    negative_aspects: ["Room"],
  },
  {
    review_id: "rev-service-en",
    property_id: "mus-pineview",
    text: "service was slow and the wifi failed in the evening",
    detected_language: "en",
    negative_aspects: ["Service"],
  },
];

export default function ReviewRepliesPage() {
  const [draft, setDraft] = useState<ReplyDraft | null>(null);
  const [editing, setEditing] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function compose(review: (typeof SAMPLE_REVIEWS)[number]) {
    setBusy(true);
    setStatus(null);
    try {
      const res = await api.draftReply(review);
      setDraft(res.reply);
      setEditing(res.reply.body);
    } catch {
      // The draft is generated live from logged complaints/interventions and
      // property facts. If the backend is unreachable we surface that honestly
      // rather than fabricating a reply that looks grounded.
      setDraft(null);
      setStatus("Could not reach the backend to draft a reply. Start the API and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!draft) return;
    setBusy(true);
    try {
      const res = await api.approveReply(draft.id, "owner@pineview", editing);
      setDraft(res.reply);
      setStatus("Reply approved and marked ready to post.");
    } catch {
      setStatus("Could not reach the backend to approve the reply. Start the API and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · F13"
        title="Closed-Loop Review Replies"
        description="Drafts a reply in the review's detected language. Where a resolved complaint or logged intervention matches the review's negative aspects, the draft cites the logged fix. Guest PII, room numbers and internal staff names are excluded, and only facts from complaints, interventions and property facts are stated. A manager must approve or edit before it is marked ready to post."
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Card title="Reviews needing a reply" subtitle="Pick one to draft a reply">
          <ul className="space-y-2">
            {SAMPLE_REVIEWS.map((r) => (
              <li key={r.review_id}>
                <button
                  type="button"
                  onClick={() => compose(r)}
                  disabled={busy}
                  className="w-full rounded-lg border border-mist-300 bg-mist-50 px-3 py-2 text-left hover:bg-mist-100"
                >
                  <div className="flex items-center gap-2">
                    <Badge tone="neutral">{r.detected_language}</Badge>
                    {r.negative_aspects.map((a) => (
                      <Badge key={a} tone="dawn">
                        {a}
                      </Badge>
                    ))}
                  </div>
                  <p className="mt-1 text-sm text-forest-700">“{r.text}”</p>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          title={draft ? `Draft reply · ${draft.language}` : "Draft reply"}
          subtitle="Manager approval required before posting"
        >
          {!draft ? (
            <p className="text-sm text-forest-600">
              Select a review to generate a fact-grounded draft reply.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={draft.state === "ready_to_post" ? "forest" : "neutral"}>
                  {draft.state}
                </Badge>
                {draft.template_generated && (
                  <Badge tone="pine">template-generated</Badge>
                )}
                {draft.pii_redacted && <Badge tone="forest">PII redacted</Badge>}
                {draft.cited_source && (
                  <Badge tone="dawn">cites {draft.cited_source}</Badge>
                )}
              </div>

              {draft.cited_fix && (
                <p className="rounded-lg bg-forest-100 p-2 text-xs text-forest-700">
                  Cited logged fix: {draft.cited_fix}
                </p>
              )}

              <textarea
                aria-label="Reply body"
                value={editing}
                onChange={(e) => setEditing(e.target.value)}
                rows={6}
                disabled={draft.state === "ready_to_post"}
                className="w-full rounded-xl border border-mist-300 p-3 text-sm"
              />

              {draft.state !== "ready_to_post" ? (
                <Button onClick={approve} disabled={busy}>
                  Approve &amp; mark ready to post
                </Button>
              ) : (
                <p className="text-sm text-forest-600">
                  Approved by {draft.approved_by}. Ready to post.
                </p>
              )}
              {status && <p className="text-sm text-pine-600">{status}</p>}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
