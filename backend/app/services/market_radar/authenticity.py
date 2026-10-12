"""F9 Authenticity-Adjusted Benchmarks (Req 23).

Reviews are flagged for three *suspicious signals* (never "confirmed fake",
Req 23.5):

* **burst** — the review falls on a day whose review count for its property
  exceeds the 28-day rolling mean + 3 standard deviations (Req 23.1).
* **near-duplicate** — its text has cosine similarity >= 0.9 (bag-of-words TF)
  with another review (Req 23.2).
* **single-review author** — the platform exposes reviewer history and the
  author has only this one review (Req 23.3).

A 0..1 suspicion score is combined from the flags (Req 23.4). An *adjusted
view* recomputes the Cluster rankings excluding reviews with suspicion >= 0.7
and shows the original vs adjusted rank side by side (Req 23.6).

To give these signals real depth the module uses a dedicated, seed-reproducible
authenticity panel (``_build_panel``) that deliberately injects a review burst,
a near-duplicate cluster and single-review authors on one property. The panel
is documented synthetic data (same honesty note as the analytics panel).
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache

from app.seed.sample_reviews import PROPERTIES

NEAR_DUPLICATE_THRESHOLD = 0.9
BURST_SD_MULTIPLIER = 3.0
ROLLING_WINDOW_DAYS = 28
SUSPICION_EXCLUDE_THRESHOLD = 0.7


@dataclass
class AuthReview:
    """A review on the authenticity panel."""

    id: str
    property_id: str
    property_name: str
    platform: str
    author: str
    date: date
    rating: float
    text: str
    reviewer_history_available: bool
    source_url: str | None


@dataclass
class ReviewFlags:
    """Suspicious-signal flags + suspicion score for one review (Req 23)."""

    review_id: str
    property_id: str
    burst: bool = False
    near_duplicate: bool = False
    single_review_author: bool = False
    suspicion: float = 0.0
    duplicate_of: list[str] = field(default_factory=list)

    @property
    def any_flag(self) -> bool:
        return self.burst or self.near_duplicate or self.single_review_author

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "property_id": self.property_id,
            "burst": self.burst,
            "near_duplicate": self.near_duplicate,
            "single_review_author": self.single_review_author,
            "suspicion": round(self.suspicion, 3),
            "duplicate_of": self.duplicate_of,
            "label": "suspicious signals",
        }


def _tokens(text: str) -> Counter:
    return Counter(w for w in text.lower().split())


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Deterministic authenticity panel (documented synthetic data).
# ---------------------------------------------------------------------------
# Vocabulary pools used to synthesise a *unique* genuine review per record so
# that genuine reviews stay well below the 0.9 near-duplicate threshold with one
# another; only the injected promotional campaign uses one identical text.
_SUBJECTS = ["rooms", "food", "staff", "location", "housekeeping", "value", "views", "service"]
_ADJECTIVES = [
    "clean", "cosy", "spacious", "friendly", "tasty", "prompt", "quiet", "scenic",
    "comfortable", "warm", "tidy", "helpful", "central", "charming", "relaxing",
]
_SCENES = [
    "overlooking the Doon valley", "a short walk from Mall Road", "near Camel's Back",
    "with a misty morning view", "beside the deodar grove", "on a quiet ridge",
    "close to the Gun Hill ropeway", "with a sunny balcony", "by the pine forest",
    "under a clear mountain sky", "with easy parking", "a few steps from the market",
]
_DUP_TEXT = "best hotel in mussoorie amazing staff amazing rooms book now"
_URL = "https://www.google.com/maps/place/{slug}-mussoorie"


@lru_cache(maxsize=4)
def _build_panel(seed: int = 20240601, today_iso: str | None = None) -> tuple[AuthReview, ...]:
    today = date.fromisoformat(today_iso) if today_iso else date(2024, 6, 15)
    rng = random.Random(seed)
    names = [p.name for p in PROPERTIES]
    out: list[AuthReview] = []
    counter = 0

    def _slug(pid: str) -> str:
        return pid.replace("mus-", "")

    for pi, prop in enumerate(PROPERTIES):
        pname = names[pi]
        # Baseline genuine reviews spread over the last ~90 days. Each gets a
        # couple of unique tokens so genuine reviews are NOT near-duplicates of
        # each other (keeps the near-duplicate signal specific to the campaign).
        n_genuine = 24
        for gi in range(n_genuine):
            counter += 1
            day_offset = rng.randint(1, 90)
            # Compose a unique genuine review from independent word pools.
            adjs = rng.sample(_ADJECTIVES, 3)
            subs = rng.sample(_SUBJECTS, 2)
            scene = _SCENES[rng.randrange(len(_SCENES))]
            text = (
                f"the {subs[0]} were {adjs[0]} and {adjs[1]}, "
                f"{subs[1]} {adjs[2]} {scene}"
            )
            # Genuine authors are drawn from a pool so they have reviewer
            # history (> 1 review); the single-review signal then specifically
            # catches the injected campaign's throwaway accounts (Req 23.3).
            author = f"guest-{prop.property_id}-{gi % 10}"
            out.append(
                AuthReview(
                    id=f"ar-{counter:04d}",
                    property_id=prop.property_id,
                    property_name=pname,
                    platform="Google",
                    author=author,
                    date=today - timedelta(days=day_offset),
                    rating=float(rng.choice([4, 5, 4, 5, 3])),
                    text=text,
                    reviewer_history_available=True,
                    source_url=_URL.format(slug=_slug(prop.property_id)),
                )
            )

    # Inject a promotional campaign on the first property: a one-day burst of
    # near-duplicate 5-star reviews from single-review authors.
    boosted = PROPERTIES[0]
    burst_day = today - timedelta(days=10)
    for _ in range(14):
        counter += 1
        out.append(
            AuthReview(
                id=f"ar-{counter:04d}",
                property_id=boosted.property_id,
                property_name=boosted.name,
                platform="Google",
                author=f"newuser-{counter}",  # single-review authors
                date=burst_day,
                rating=5.0,
                text=_DUP_TEXT,
                reviewer_history_available=True,
                source_url=_URL.format(slug=_slug(boosted.property_id)),
            )
        )
    return tuple(out)


class AuthenticityFilter:
    """Flag suspicious signals + recompute adjusted Cluster rankings (Req 23)."""

    def __init__(self, reviews: tuple[AuthReview, ...] | None = None) -> None:
        self._reviews = reviews if reviews is not None else _build_panel()

    def _burst_ids(self) -> set[str]:
        """IDs of reviews on a burst day (daily count > 28-day mean + 3 SD)."""
        flagged: set[str] = set()
        by_prop: dict[str, list[AuthReview]] = defaultdict(list)
        for r in self._reviews:
            by_prop[r.property_id].append(r)
        for reviews in by_prop.values():
            per_day: Counter = Counter(r.date for r in reviews)
            days = sorted(per_day)
            for d in days:
                window = [
                    per_day[dd]
                    for dd in days
                    if timedelta(0) <= (d - dd) < timedelta(days=ROLLING_WINDOW_DAYS)
                    and dd < d
                ]
                if len(window) < 3:
                    continue
                mean = sum(window) / len(window)
                var = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
                sd = math.sqrt(var)
                threshold = mean + BURST_SD_MULTIPLIER * sd
                if per_day[d] > threshold:
                    for r in reviews:
                        if r.date == d:
                            flagged.add(r.id)
        return flagged

    def _near_duplicates(self) -> dict[str, list[str]]:
        """Map each review id to the ids it is a near-duplicate of."""
        vecs = {r.id: _tokens(r.text) for r in self._reviews}
        ids = [r.id for r in self._reviews]
        dup: dict[str, list[str]] = defaultdict(list)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                sim = _cosine(vecs[ids[i]], vecs[ids[j]])
                if sim >= NEAR_DUPLICATE_THRESHOLD:
                    dup[ids[i]].append(ids[j])
                    dup[ids[j]].append(ids[i])
        return dup

    def _single_review_authors(self) -> set[str]:
        counts: Counter = Counter(
            r.author for r in self._reviews if r.reviewer_history_available
        )
        return {
            r.id
            for r in self._reviews
            if r.reviewer_history_available and counts[r.author] == 1
        }

    def flags(self) -> dict[str, ReviewFlags]:
        burst = self._burst_ids()
        dup = self._near_duplicates()
        singles = self._single_review_authors()
        out: dict[str, ReviewFlags] = {}
        for r in self._reviews:
            f = ReviewFlags(review_id=r.id, property_id=r.property_id)
            f.burst = r.id in burst
            f.near_duplicate = r.id in dup
            f.duplicate_of = sorted(dup.get(r.id, []))
            f.single_review_author = r.id in singles
            # Suspicion score: weighted combination of the three signals in 0..1.
            score = 0.0
            if f.burst:
                score += 0.4
            if f.near_duplicate:
                score += 0.4
            if f.single_review_author:
                score += 0.3
            f.suspicion = min(1.0, score)
            out[r.id] = f
        return out

    def _rank(self, exclude: set[str]) -> list[tuple[str, float, int]]:
        """Rank properties by mean rating; return (property_id, mean, rank)."""
        sums: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for r in self._reviews:
            if r.id in exclude:
                continue
            sums[r.property_id] += r.rating
            counts[r.property_id] += 1
        means = {
            pid: (sums[pid] / counts[pid] if counts[pid] else 0.0)
            for pid in {p.property_id for p in PROPERTIES}
        }
        ordered = sorted(means.items(), key=lambda kv: kv[1], reverse=True)
        return [(pid, mean, i + 1) for i, (pid, mean) in enumerate(ordered)]

    def adjusted_view(self) -> dict:
        flags = self.flags()
        excluded = {
            rid for rid, f in flags.items() if f.suspicion >= SUSPICION_EXCLUDE_THRESHOLD
        }
        original = {pid: rank for pid, _, rank in self._rank(set())}
        original_mean = {pid: mean for pid, mean, _ in self._rank(set())}
        adjusted = self._rank(excluded)
        names = {p.property_id: p.name for p in PROPERTIES}
        rows = []
        for pid, adj_mean, adj_rank in adjusted:
            rows.append(
                {
                    "property_id": pid,
                    "property_name": names[pid],
                    "original_rank": original[pid],
                    "original_mean": round(original_mean[pid], 3),
                    "adjusted_rank": adj_rank,
                    "adjusted_mean": round(adj_mean, 3),
                    "rank_delta": original[pid] - adj_rank,
                }
            )
        rows.sort(key=lambda r: r["adjusted_rank"])
        flagged_rows = [
            {
                **flags[r.id].to_dict(),
                "property_name": r.property_name,
                "platform": r.platform,
                "date": r.date.isoformat(),
                "rating": r.rating,
                "text": r.text,
                "source_url": r.source_url or "source URL unavailable",
            }
            for r in self._reviews
            if flags[r.id].any_flag
        ]
        flagged_rows.sort(key=lambda r: r["suspicion"], reverse=True)
        return {
            "suspicion_exclude_threshold": SUSPICION_EXCLUDE_THRESHOLD,
            "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
            "excluded_count": len(excluded),
            "total_reviews": len(self._reviews),
            "rankings": rows,
            "flagged_reviews": flagged_rows,
        }


@lru_cache
def get_authenticity_filter() -> AuthenticityFilter:
    return AuthenticityFilter()
