"""The Hinglish Accuracy Benchmark harness (Req 16).

Loads the held-out Hinglish_Test_Set, runs every :class:`BenchmarkSystem` over
it, and reports — per system — the macro-F1 for:

* overall sentiment,
* aspect detection (which aspects are mentioned), and
* aspect sentiment (the polarity of each detected-and-gold aspect),

each with a seeded 95% bootstrap confidence interval, plus a per-Aspect
confusion matrix. The whole run is deterministic for a fixed seed and model
versions (Req 16.8). The test set is validated to be disjoint from any
Sentiment_Engine training vocabulary by a dedicated test (Req 16.6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.benchmark.metrics import (
    bootstrap_ci,
    confusion_matrix,
    detection_f1,
    macro_f1,
)
from app.benchmark.systems import (
    ALL_ASPECTS_FALLBACK,
    BenchmarkSystem,
    default_systems,
)

TEST_SET_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "hinglish_test_set"
    / "hinglish_test_set.json"
)
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "benchmark"
DEFAULT_SEED = 20240601


@dataclass
class SystemReport:
    name: str
    overall_f1: float
    overall_ci: tuple[float, float]
    aspect_detection_f1: float
    aspect_detection_ci: tuple[float, float]
    aspect_sentiment_f1: float
    aspect_sentiment_ci: tuple[float, float]
    confusion: dict[str, dict[str, int]]
    aspect_confusion: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "overall_sentiment": {
                "macro_f1": round(self.overall_f1, 4),
                "ci_95": list(self.overall_ci),
            },
            "aspect_detection": {
                "macro_f1": round(self.aspect_detection_f1, 4),
                "ci_95": list(self.aspect_detection_ci),
            },
            "aspect_sentiment": {
                "macro_f1": round(self.aspect_sentiment_f1, 4),
                "ci_95": list(self.aspect_sentiment_ci),
            },
            "confusion_matrix": self.confusion,
            "aspect_confusion": self.aspect_confusion,
        }


@dataclass
class BenchmarkResult:
    seed: int
    test_set_size: int
    systems: list[SystemReport]

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "test_set_size": self.test_set_size,
            "systems": [s.to_dict() for s in self.systems],
        }


def load_test_set(path: Path = TEST_SET_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _aspect_universe(records: list[dict]) -> list[str]:
    seen: set[str] = set()
    for rec in records:
        seen.update(rec["aspect_labels"].keys())
    return sorted(seen or ALL_ASPECTS_FALLBACK)


def evaluate_system(
    system: BenchmarkSystem,
    records: list[dict],
    seed: int,
) -> SystemReport:
    aspects = _aspect_universe(records)
    overall_pairs: list[tuple[str, str]] = []
    detection_pairs: list[tuple[bool, bool]] = []
    aspect_sentiment_pairs: list[tuple[str, str]] = []
    aspect_conf: dict[str, dict[str, dict[str, int]]] = {}
    per_aspect_pairs: dict[str, list[tuple[str, str]]] = {a: [] for a in aspects}

    for rec in records:
        pred = system.predict(rec["text"])
        overall_pairs.append((rec["overall_label"], pred.overall_label))
        gold_aspects = rec["aspect_labels"]
        for aspect in aspects:
            gold_present = aspect in gold_aspects
            pred_present = aspect in pred.aspect_labels
            detection_pairs.append((gold_present, pred_present))
            if gold_present and pred_present:
                gold_lbl = gold_aspects[aspect]
                pred_lbl = pred.aspect_labels[aspect]
                aspect_sentiment_pairs.append((gold_lbl, pred_lbl))
                per_aspect_pairs[aspect].append((gold_lbl, pred_lbl))

    for aspect, pairs in per_aspect_pairs.items():
        aspect_conf[aspect] = {
            "matrix": confusion_matrix(pairs),
            "support": {"n": len(pairs)},
        }

    return SystemReport(
        name=system.name,
        overall_f1=macro_f1(overall_pairs),
        overall_ci=bootstrap_ci(overall_pairs, macro_f1, seed=seed),
        aspect_detection_f1=detection_f1(detection_pairs),
        aspect_detection_ci=bootstrap_ci(detection_pairs, detection_f1, seed=seed + 1),
        aspect_sentiment_f1=macro_f1(aspect_sentiment_pairs),
        aspect_sentiment_ci=bootstrap_ci(aspect_sentiment_pairs, macro_f1, seed=seed + 2),
        confusion=confusion_matrix(overall_pairs),
        aspect_confusion=aspect_conf,
    )


def run_benchmark(
    systems: list[BenchmarkSystem] | None = None,
    seed: int = DEFAULT_SEED,
    records: list[dict] | None = None,
) -> BenchmarkResult:
    records = records if records is not None else load_test_set()
    systems = systems or default_systems()
    reports = [evaluate_system(s, records, seed=seed) for s in systems]
    return BenchmarkResult(seed=seed, test_set_size=len(records), systems=reports)


def write_outputs(result: BenchmarkResult, out_dir: Path = OUTPUT_DIR) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "benchmark_results.json"
    md_path = out_dir / "benchmark_results.md"
    json_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(result), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _render_markdown(result: BenchmarkResult) -> str:
    lines = [
        "# Hinglish Accuracy Benchmark",
        "",
        f"- Test set size: **{result.test_set_size}** reviews",
        f"- Seed: **{result.seed}** (idempotent for a fixed seed, Req 16.8)",
        "",
        "## Macro-F1 by system (95% bootstrap CI)",
        "",
        "| System | Overall sentiment | Aspect detection | Aspect sentiment |",
        "| --- | --- | --- | --- |",
    ]
    for s in result.systems:
        lines.append(
            f"| {s.name} "
            f"| {s.overall_f1:.3f} [{s.overall_ci[0]:.3f}, {s.overall_ci[1]:.3f}] "
            f"| {s.aspect_detection_f1:.3f} "
            f"[{s.aspect_detection_ci[0]:.3f}, {s.aspect_detection_ci[1]:.3f}] "
            f"| {s.aspect_sentiment_f1:.3f} "
            f"[{s.aspect_sentiment_ci[0]:.3f}, {s.aspect_sentiment_ci[1]:.3f}] |"
        )
    lines.append("")
    return "\n".join(lines)
