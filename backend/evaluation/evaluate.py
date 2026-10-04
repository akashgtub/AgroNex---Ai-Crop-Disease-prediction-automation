"""
AgroNex Disease Model Evaluation CLI
Command-line interface for running quantitative benchmarks on the ONNX model.

Usage Examples:
  # Evaluate an ImageFolder dataset:
  python evaluate.py --data-path /path/to/dataset --mode direct

  # Compare direct vs letterbox vs TTA on the same dataset:
  python evaluate.py --data-path /path/to/dataset --compare-all

  # Run verification test on a synthetic labeled test fixture:
  python evaluate.py --run-test-fixture
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import numpy as np
from PIL import Image

# Ensure backend root is accessible
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from evaluation.evaluator import ModelEvaluator


def generate_synthetic_evaluation_fixture(temp_dir: Path, num_classes: int = 5, samples_per_class: int = 3) -> Path:
    """Generates a small labeled ImageFolder fixture for testing the evaluation pipeline."""
    evaluator = ModelEvaluator()
    classes = evaluator.classes[:num_classes]

    for class_name in classes:
        class_dir = temp_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        for i in range(samples_per_class):
            img_path = class_dir / f"sample_{i:02d}.jpg"
            # Generate leaf-like image with class-specific hue
            arr = np.full((250, 250, 3), 235, dtype=np.uint8)
            y, x = np.ogrid[:250, :250]
            mask = ((x - 125) ** 2) / (90 ** 2) + ((y - 125) ** 2) / (100 ** 2) <= 1.0
            arr[mask] = (40 + i * 10, 140, 50)
            Image.fromarray(arr).save(img_path)

    return temp_dir


def main():
    parser = argparse.ArgumentParser(
        description="AgroNex Plant Disease ONNX Model Quantitative Evaluator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Note: The repository currently contains no formal labeled test split.
Provide a labeled ImageFolder directory or CSV/JSONL manifest to compute quantitative metrics.
        """
    )
    parser.add_argument(
        "--data-path", "-d",
        type=str,
        default=None,
        help="Path to labeled evaluation dataset: directory (ImageFolder), CSV, or JSONL manifest."
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["direct", "letterbox"],
        default="direct",
        help="Preprocessing strategy: 'direct' (production baseline) or 'letterbox' (aspect-preserving)."
    )
    parser.add_argument(
        "--enable-tta",
        action="store_true",
        help="Enable multi-view Test-Time Augmentation (averaging horizontal flip)."
    )
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="Run comparative evaluation across direct, letterbox, and TTA on the same dataset."
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="evaluation_results.json",
        help="File path to save the full evaluation JSON report."
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="per_class_metrics.csv",
        help="File path to save per-class tabular metrics CSV."
    )
    parser.add_argument(
        "--run-test-fixture",
        action="store_true",
        help="Generate a small synthetic labeled test dataset and run the evaluator end-to-end to verify functionality."
    )

    args = parser.parse_args()
    evaluator = ModelEvaluator()

    # 1. Handle Test Fixture Mode
    if args.run_test_fixture:
        print("\n[INFO] Running evaluation pipeline self-test using a synthetic labeled fixture...")
        temp_dir = Path(tempfile.mkdtemp(prefix="agronex_eval_test_"))
        try:
            fixture_path = generate_synthetic_evaluation_fixture(temp_dir, num_classes=4, samples_per_class=2)
            dataset = evaluator.load_dataset(fixture_path)
            print(f"[INFO] Successfully loaded {len(dataset)} labeled samples across 4 classes from fixture.")

            # Run evaluation
            results = evaluator.evaluate(dataset, preprocessing_mode="direct", enable_tta=False)
            evaluator.print_summary(results)
            print("[INFO] Evaluator pipeline self-test completed successfully!")
            return
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # 2. Check if data path is provided
    if not args.data_path:
        print("\n" + "=" * 70)
        print("          AGRONEX EVALUATION MODULE: NO DATASET PROVIDED          ")
        print("=" * 70)
        print("Error: No labeled dataset source was specified.")
        print("\nReason:")
        print("  Quantitative accuracy and F1 evaluation require a verified ground-truth dataset.")
        print("  The repository does not bundle an uncompressed 54,000-image evaluation split.")
        print("\nHow to run:")
        print("  1. With an ImageFolder directory:")
        print("     python evaluate.py --data-path path/to/labeled_test_dir")
        print("\n  2. With a CSV manifest (headers: image_path, label):")
        print("     python evaluate.py --data-path path/to/manifest.csv")
        print("\n  3. Verify the evaluator with a self-contained synthetic fixture:")
        print("     python evaluate.py --run-test-fixture")
        print("=" * 70 + "\n")
        sys.exit(1)

    # 3. Load dataset
    try:
        dataset = evaluator.load_dataset(args.data_path)
    except Exception as e:
        print(f"\n[ERROR] Failed to load dataset: {e}\n")
        sys.exit(1)

    print(f"[INFO] Loaded {len(dataset)} labeled images from: {args.data_path}")

    # 4. Comparative Evaluation Mode
    if args.compare_all:
        print("\n[INFO] Running comparative evaluation across strategies on identical dataset:")
        strategies = [
            ("direct", False, "Direct Squish (Baseline Production)"),
            ("letterbox", False, "Letterbox Padding (Aspect-Preserving)"),
            ("direct", True, "Direct Squish + TTA (2-View Batched)")
        ]
        comparison_table = []

        for mode, tta, label in strategies:
            print(f"  -> Evaluating: {label}...")
            res = evaluator.evaluate(dataset, preprocessing_mode=mode, enable_tta=tta)
            om = res["overall_metrics"]
            lat = res["latency"]
            comparison_table.append({
                "Strategy": label,
                "Accuracy": f"{om['overall_accuracy'] * 100:.2f}%",
                "Macro F1": f"{om['macro_f1'] * 100:.2f}%",
                "Weighted F1": f"{om['weighted_f1'] * 100:.2f}%",
                "ECE": f"{om['expected_calibration_error'] * 100:.2f}%",
                "Avg Latency": f"{lat['average_ms']:.2f} ms"
            })

        print("\n" + "=" * 90)
        print("                     COMPARATIVE STRATEGY BENCHMARK REPORT                    ")
        print("=" * 90)
        print(f"{'Strategy':<40} | {'Accuracy':<10} | {'Macro F1':<10} | {'Weighted F1':<12} | {'ECE':<8} | {'Latency'}")
        print("-" * 90)
        for row in comparison_table:
            print(f"{row['Strategy']:<40} | {row['Accuracy']:<10} | {row['Macro F1']:<10} | {row['Weighted F1']:<12} | {row['ECE']:<8} | {row['Avg Latency']}")
        print("=" * 90)
        print("Note: Behavioral differences do not indicate real-world field superiority unless verified against field test sets.\n")
        return

    # 5. Single Strategy Evaluation
    results = evaluator.evaluate(dataset, preprocessing_mode=args.mode, enable_tta=args.enable_tta)
    evaluator.print_summary(results)

    # 6. Save reports
    evaluator.export_json(results, args.output_json)
    evaluator.export_per_class_csv(results, args.output_csv)
    print(f"[INFO] Detailed evaluation JSON exported to: {args.output_json}")
    print(f"[INFO] Per-class CSV metrics exported to:    {args.output_csv}")


if __name__ == "__main__":
    main()
