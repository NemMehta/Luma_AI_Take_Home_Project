"""Benchmark the failure classifier against the labeled corpus.

Reads the corpus manifest, runs the existing classifier on each labeled FAILING
trace, compares the prediction to the manifest's true label, and prints accuracy
plus a confusion matrix. Also writes a results JSON.

Measurement only — the LLM is called solely through app.diagnosis.classifier.

Run from the repo root:  python -m harness.benchmark [path/to/manifest.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.diagnosis.classifier import classify_trace

DEFAULT_MANIFEST = "harness/corpus/manifest.json"
RESULTS_PATH = "harness/benchmark_results.json"


def run_benchmark(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text())
    corpus_dir = manifest_path.parent
    failing = [t for t in manifest.get("traces", []) if t.get("outcome") == "fail"]

    predictions, errors = [], []
    for trace in failing:
        name, true_label = trace.get("file"), trace.get("label")
        zip_path = corpus_dir / name
        if not zip_path.is_file():
            errors.append({"file": name, "true_label": true_label, "error": "trace file not found"})
            print(f"  {'MISSING':<8} {name}: trace file not found")
            continue
        try:
            result = classify_trace(str(zip_path))
        except Exception as exc:  # surface failures, never hide them
            errors.append({"file": name, "true_label": true_label, "error": f"{type(exc).__name__}: {exc}"})
            print(f"  {'ERROR':<8} {name}: classification failed — {type(exc).__name__}: {exc}")
            continue
        predicted = result.category.value
        correct = predicted == true_label
        predictions.append({
            "file": name,
            "true_label": true_label,
            "predicted": predicted,
            "correct": correct,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        })
        tag = "OK" if correct else "WRONG"
        print(f"  {tag:<8} {name}: true={true_label}  pred={predicted}  (conf {result.confidence})")

    return predictions, errors


def confusion_matrix(predictions):
    true_labels = sorted({p["true_label"] for p in predictions})
    cols = sorted({p["true_label"] for p in predictions} | {p["predicted"] for p in predictions})
    matrix = {t: {c: 0 for c in cols} for t in true_labels}
    for p in predictions:
        matrix[p["true_label"]][p["predicted"]] += 1
    return true_labels, cols, matrix


def print_matrix(true_labels, cols, matrix):
    lw = max([len(t) for t in true_labels] + [len("true \\ pred")])
    cw = max([len(c) for c in cols] + [3])
    print("true \\ pred".ljust(lw) + "  " + "  ".join(c.rjust(cw) for c in cols))
    for t in true_labels:
        print(t.ljust(lw) + "  " + "  ".join(str(matrix[t][c]).rjust(cw) for c in cols))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    manifest_path = Path(argv[0]) if argv else Path(DEFAULT_MANIFEST)
    if not manifest_path.is_file():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    load_dotenv()  # entry point: load the provider key from .env

    print(f"Benchmarking failing traces from {manifest_path}\n")
    predictions, errors = run_benchmark(manifest_path)

    classified = len(predictions)
    correct = sum(p["correct"] for p in predictions)
    accuracy = correct / classified if classified else 0.0

    true_labels, cols, matrix = [], [], {}
    if predictions:
        true_labels, cols, matrix = confusion_matrix(predictions)

    print(f"\nAccuracy: {correct}/{classified} = {accuracy:.1%}"
          + (f"   ({len(errors)} not classified)" if errors else ""))
    if predictions:
        print("\nConfusion matrix (rows = true, cols = predicted):")
        print_matrix(true_labels, cols, matrix)
    if errors:
        print("\nNot classified:")
        for e in errors:
            print(f"  - {e['file']} (true={e['true_label']}): {e['error']}")

    results = {
        "manifest": str(manifest_path),
        "accuracy": accuracy,
        "correct": correct,
        "classified": classified,
        "total_failing": classified + len(errors),
        "confusion_matrix": matrix,
        "predictions": predictions,
        "errors": errors,
    }
    Path(RESULTS_PATH).write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nWrote {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
