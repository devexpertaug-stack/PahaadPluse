"""CLI entrypoint: ``uv run python -m app.benchmark.run`` (Req 16).

Runs the Hinglish Accuracy Benchmark with a fixed seed and writes the results
table + per-Aspect confusion matrices to ``data/benchmark/``. Deterministic for
a fixed seed (Req 16.8), so running twice yields byte-identical outputs.
"""

from __future__ import annotations

import argparse

from app.benchmark.harness import DEFAULT_SEED, run_benchmark, write_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hinglish accuracy benchmark.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    result = run_benchmark(seed=args.seed)
    paths = write_outputs(result)

    print(f"Hinglish benchmark (seed={result.seed}, n={result.test_set_size})")
    for system in result.systems:
        print(
            f"  {system.name}: overall={system.overall_f1:.3f} "
            f"detection={system.aspect_detection_f1:.3f} "
            f"aspect_sentiment={system.aspect_sentiment_f1:.3f}"
        )
    print(f"Wrote {paths['json']}")
    print(f"Wrote {paths['markdown']}")


if __name__ == "__main__":
    main()
