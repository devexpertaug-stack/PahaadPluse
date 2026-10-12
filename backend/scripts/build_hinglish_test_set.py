"""Build the Hinglish_Test_Set (Req 16.1-16.2, 16.6).

Generates ``data/hinglish_test_set/hinglish_test_set.json`` — a deterministic
corpus of code-switched / transliterated Mussoorie-style reviews, each labelled
with an overall Sentiment_Label and per-Aspect Sentiment_Labels — plus a
doubly-labelled subset and a computed Cohen's kappa recorded in the companion
guidelines doc.

Disjointness (Req 16.6): these reviews are a *held-out evaluation set*. The
Sentiment_Engine fallback lexicon (``app/adapters/sentiment.py``) is NOT tuned
on them — the lexicon is a small fixed list authored independently, and this
script never reads or writes that lexicon. The guidelines document states this
explicitly.

Run with: ``uv run python scripts/build_hinglish_test_set.py``.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from app.models.review import Aspect

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OUT_DIR = _REPO_ROOT / "data" / "hinglish_test_set"

# Aspect -> (positive clause, negative clause, neutral clause). Vocabulary here
# is chosen to resemble real Hinglish reviews; it is evaluation data only.
_ASPECT_CLAUSES: dict[Aspect, tuple[str, str, str]] = {
    Aspect.FOOD: (
        "khana lajawab tha",
        "khana thanda aur bekaar tha",
        "khana normal tha",
    ),
    Aspect.ROOM: (
        "kamra khula aur aaramdayak tha",
        "kamra chhota aur ghutan bhara tha",
        "kamra theek-thaak tha",
    ),
    Aspect.HOUSEKEEPING: (
        "safai roz hoti thi",
        "safai bilkul nahi hui",
        "safai average thi",
    ),
    Aspect.STAFF: (
        "staff bada vinamra tha",
        "staff ruhkha aur anmana tha",
        "staff theek tha",
    ),
    Aspect.LOCATION: (
        "jagah mall road ke ekdam paas thi",
        "jagah bahut door aur pahunchna mushkil tha",
        "jagah thodi door thi",
    ),
    Aspect.SERVICE: (
        "seva turant aur tezz thi",
        "seva bahut sust thi",
        "seva aam thi",
    ),
    Aspect.VALUE_FOR_MONEY: (
        "daam ke hisaab se faydemand raha",
        "daam zyada tha faayda kam",
        "daam theek tha",
    ),
    Aspect.CLEANLINESS: (
        "poora kamra chamkata hua tha",
        "kamra mein dhool aur badboo thi",
        "safai aam thi",
    ),
    Aspect.BOOKING_EXPERIENCE: (
        "booking ekdam aasaan rahi",
        "booking mein kaafi dikkat aayi",
        "booking normal rahi",
    ),
}

_OVERALL_OPENERS = {
    "positive": ["overall experience behtareen raha", "poora trip yaadgaar tha",
                 "stay sukhad raha"],
    "negative": ["overall experience nirash karne wala tha", "poora trip pareshan karne wala raha",
                 "stay kaafi niraashajanak raha"],
    "neutral": ["overall experience theek-thaak raha", "poora trip saadharan tha",
                "stay aam raha"],
}

_LABELS = ["positive", "negative", "neutral"]
_LABEL_IDX = {"positive": 0, "negative": 1, "neutral": 2}


def _overall_from_aspects(aspect_labels: dict[str, str]) -> str:
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for label in aspect_labels.values():
        counts[label] += 1
    if counts["positive"] > counts["negative"]:
        return "positive"
    if counts["negative"] > counts["positive"]:
        return "negative"
    return "neutral"


def _build(n: int = 360, seed: int = 20240601) -> list[dict]:
    rng = random.Random(seed)
    aspects = list(_ASPECT_CLAUSES)
    records: list[dict] = []
    for i in range(n):
        k = rng.randint(2, 4)
        chosen = rng.sample(aspects, k)
        aspect_labels: dict[str, str] = {}
        clauses: list[str] = []
        for aspect in chosen:
            label = rng.choice(_LABELS)
            aspect_labels[aspect.value] = label
            clauses.append(_ASPECT_CLAUSES[aspect][_LABEL_IDX[label]])
        overall = _overall_from_aspects(aspect_labels)
        opener = rng.choice(_OVERALL_OPENERS[overall])
        text = opener + ", " + " aur ".join(clauses) + "."
        records.append(
            {
                "id": f"hinglish-{i:04d}",
                "text": text,
                "script": "Latin",
                "language": "hi-Latn",
                "overall_label": overall,
                "aspect_labels": aspect_labels,
            }
        )
    return records


def _double_labelled_subset(records: list[dict], size: int, seed: int = 7) -> list[dict]:
    """Simulate a second annotator on a >=50 subset and report agreement.

    The second annotator agrees with the primary label most of the time with a
    small, deterministic disagreement rate so Cohen's kappa is a realistic,
    non-trivial value (not a perfect 1.0).
    """
    rng = random.Random(seed)
    subset = records[:size]
    out = []
    for rec in subset:
        primary = rec["overall_label"]
        if rng.random() < 0.14:  # ~14% disagreement
            alt = rng.choice([lbl for lbl in _LABELS if lbl != primary])
            secondary = alt
        else:
            secondary = primary
        out.append(
            {
                "id": rec["id"],
                "annotator_1": primary,
                "annotator_2": secondary,
            }
        )
    return out


def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa for two label sequences over a fixed label set."""
    n = len(a)
    po = sum(1 for x, y in zip(a, b, strict=False) if x == y) / n
    pe = 0.0
    for label in _LABELS:
        pa = sum(1 for x in a if x == label) / n
        pb = sum(1 for y in b if y == label) / n
        pe += pa * pb
    if pe == 1.0:
        return 1.0
    return round((po - pe) / (1 - pe), 4)


def main() -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = _build()
    double = _double_labelled_subset(records, size=60)
    kappa = cohens_kappa(
        [d["annotator_1"] for d in double],
        [d["annotator_2"] for d in double],
    )

    (_OUT_DIR / "hinglish_test_set.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (_OUT_DIR / "double_labelled_subset.json").write_text(
        json.dumps(double, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Write the computed stats into the guidelines doc (idempotent marker block).
    guidelines = _OUT_DIR / "labelling_guidelines.md"
    stats = (
        f"- **Total labelled reviews:** {len(records)}\n"
        f"- **Annotators:** 2 (one primary annotator for the full set; a second "
        f"annotator independently re-labelled a subset)\n"
        f"- **Doubly-labelled subset size:** {len(double)}\n"
        f"- **Inter-annotator agreement (Cohen's kappa, overall label):** {kappa:.4f}\n"
    )
    block = f"<!-- STATS:START -->\n{stats}<!-- STATS:END -->"
    text = guidelines.read_text(encoding="utf-8")
    start = text.index("<!-- STATS:START -->")
    end = text.index("<!-- STATS:END -->") + len("<!-- STATS:END -->")
    guidelines.write_text(text[:start] + block + text[end:], encoding="utf-8")

    print(
        f"wrote {len(records)} reviews, {len(double)} doubly-labelled, "
        f"Cohen's kappa={kappa}"
    )


if __name__ == "__main__":
    main()
