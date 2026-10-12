# Risk_Scorer validation and Checkout Shield live updates

This document covers the In-Stay Sentinel Risk_Scorer (Req 15) — how it is
validated and how the Checkout Shield board stays live.

## What the Risk_Scorer does

`app/services/sentinel/risk.py` computes a `Risk_Score` in `[0, 1]` for each
in-house Stay from:

- its **Complaints** — count, urgency (P1..P4), open/resolved state and
  recurrence,
- the Stay's running **message sentiment**,
- **time to checkout**, and
- Stay attributes.

The score is a logistic over a **non-negative weighted sum** of these factors.
The board surfaces the **top-3 contributing factors** per Stay.

### Monotonicity (metamorphic property, Req 15.7)

Every open complaint contributes a non-negative amount; a resolved complaint
contributes **zero** to the open-complaint terms. The sentiment and
time-to-checkout terms depend only on the Stay, not on which complaints are
open. Therefore **resolving an open complaint (holding everything else fixed)
can never increase the score**. This is enforced as a Hypothesis
property-based test in `tests/test_risk_scorer.py`
(`test_resolving_open_complaint_never_increases_score`, 200 examples).

## Validation (held-out synthetic set)

`app/services/sentinel/validation.py` builds a deterministic held-out set of
600 labelled synthetic Stays (seed `20240601`), scores each with the production
scorer and reports ROC AUC plus a calibration table. Regenerate with:

```bash
cd backend && uv run python -m app.services.sentinel.validation
```

Latest results (committed to `data/sentinel/risk_validation.{json,md}`):

- **ROC AUC ≈ 0.85**
- **Expected calibration error (ECE) ≈ 0.10**, with a monotonically increasing
  reliability curve (see `data/sentinel/risk_validation.md`).

The dataset is synthetic because the sandbox has no real guest outcomes; the
labelling model and the scorer share factors but the label carries independent
noise, so the AUC reflects genuine ranking ability rather than a tautology.

## Live board updates (Req 15.6) — chosen mechanism

The Checkout Shield board must update **within 5 seconds without a manual
refresh**. We use **short polling**: the `/checkout-shield` page re-fetches
`GET /sentinel/board` every 4 seconds. This was chosen over WebSocket/SSE
because:

- the demo runs a single FastAPI worker with in-process state, so there is no
  fan-out problem a socket would solve;
- polling degrades gracefully and needs no sticky connections or extra
  infrastructure; and
- a 4s interval comfortably meets the 5s budget while a WhatsApp/voice complaint
  recomputes the affected Stay's score within the 10s recompute budget.

The page shows a "live" indicator and the last-updated timestamp so staff can
see it is refreshing on its own.
