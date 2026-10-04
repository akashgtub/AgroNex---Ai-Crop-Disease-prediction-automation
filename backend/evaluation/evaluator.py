"""
AgroNex Disease Model Evaluation Engine
Provides independent quantitative evaluation of the ONNX crop disease model
across ImageFolder and CSV/JSONL datasets, computing accuracy, macro/weighted F1,
confusion matrices, confidence distributions, and Expected Calibration Error (ECE).
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Ensure backend root is accessible
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.ai.disease_detector import DiseaseDetector


class ModelEvaluator:
    """
    Evaluates the AgroNex ONNX disease classifier on labeled datasets.
    Supports ImageFolder and CSV/JSONL manifests.
    Computes comprehensive multi-class metrics, confusion matrices, and calibration error.
    """

    def __init__(
        self,
        detector: Optional[DiseaseDetector] = None,
        classes_path: Optional[str] = None
    ):
        self.detector = detector or DiseaseDetector()
        self.classes: List[str] = self.detector.classes
        self.num_classes: int = len(self.classes)
        self.class_to_idx: Dict[str, int] = {cls: idx for idx, cls in enumerate(self.classes)}

    def load_dataset(self, data_source: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Loads a labeled dataset from either:
        1. An ImageFolder directory (data_dir/<class_name>/<image_file>)
        2. A CSV manifest containing 'image_path' and 'label' columns
        3. A JSONL manifest containing 'image_path' and 'label' records

        Fails gracefully with informative feedback if no valid labeled images are found.
        """
        source_path = Path(data_source)
        if not source_path.exists():
            raise FileNotFoundError(
                f"Evaluation dataset source not found at: {source_path.resolve()}\n"
                "Please provide a valid path to an ImageFolder directory, CSV, or JSONL manifest."
            )

        samples: List[Dict[str, Any]] = []

        if source_path.is_dir():
            # ImageFolder format: check subdirectories matching class names
            valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
            for class_dir in sorted(source_path.iterdir()):
                if class_dir.is_dir():
                    class_name = class_dir.name
                    if class_name in self.class_to_idx:
                        class_idx = self.class_to_idx[class_name]
                        for img_file in class_dir.iterdir():
                            if img_file.suffix.lower() in valid_exts and img_file.is_file():
                                samples.append({
                                    "image_path": str(img_file.resolve()),
                                    "true_class_name": class_name,
                                    "true_label_idx": class_idx
                                })
            if not samples:
                raise ValueError(
                    f"No valid labeled images found in directory: {source_path.resolve()}\n"
                    f"Expected subdirectories named after the 38 classes (e.g. 'Tomato___Early_blight/')."
                )

        elif source_path.suffix.lower() == ".csv":
            # CSV manifest format
            base_dir = source_path.parent
            with open(source_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                path_col = next((c for c in fieldnames if c.lower() in ("image_path", "path", "file", "image")), None)
                label_col = next((c for c in fieldnames if c.lower() in ("label", "class", "target", "class_name")), None)

                if not path_col or not label_col:
                    raise ValueError(
                        f"CSV manifest {source_path} must contain 'image_path' and 'label' headers. "
                        f"Found columns: {fieldnames}"
                    )

                for row_num, row in enumerate(reader, start=2):
                    raw_path = row[path_col].strip()
                    raw_label = row[label_col].strip()
                    img_path = Path(raw_path) if Path(raw_path).is_absolute() else base_dir / raw_path

                    if not img_path.exists():
                        continue  # Skip missing paths

                    # Resolve class label (by name or by integer index)
                    if raw_label in self.class_to_idx:
                        class_idx = self.class_to_idx[raw_label]
                        class_name = raw_label
                    elif raw_label.isdigit() and 0 <= int(raw_label) < self.num_classes:
                        class_idx = int(raw_label)
                        class_name = self.classes[class_idx]
                    else:
                        continue  # Unknown label

                    samples.append({
                        "image_path": str(img_path.resolve()),
                        "true_class_name": class_name,
                        "true_label_idx": class_idx
                    })

            if not samples:
                raise ValueError(f"No valid labeled samples could be loaded from CSV manifest: {source_path}")

        elif source_path.suffix.lower() in (".jsonl", ".json"):
            # JSONL manifest format
            base_dir = source_path.parent
            with open(source_path, mode="r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    raw_path = record.get("image_path") or record.get("path") or record.get("file")
                    raw_label = record.get("label") or record.get("class") or record.get("class_name")

                    if not raw_path or raw_label is None:
                        continue

                    img_path = Path(raw_path) if Path(raw_path).is_absolute() else base_dir / raw_path
                    if not img_path.exists():
                        continue

                    if str(raw_label) in self.class_to_idx:
                        class_idx = self.class_to_idx[str(raw_label)]
                        class_name = str(raw_label)
                    elif str(raw_label).isdigit() and 0 <= int(raw_label) < self.num_classes:
                        class_idx = int(raw_label)
                        class_name = self.classes[class_idx]
                    else:
                        continue

                    samples.append({
                        "image_path": str(img_path.resolve()),
                        "true_class_name": class_name,
                        "true_label_idx": class_idx
                    })

            if not samples:
                raise ValueError(f"No valid labeled samples could be loaded from manifest: {source_path}")

        else:
            raise ValueError(
                f"Unsupported data source format: {source_path.suffix}. "
                "Expected a directory (ImageFolder), a .csv file, or a .jsonl file."
            )

        return samples

    def evaluate(
        self,
        dataset: List[Dict[str, Any]],
        preprocessing_mode: str = "direct",
        enable_tta: bool = False
    ) -> Dict[str, Any]:
        """
        Runs evaluation across all samples in the dataset and computes:
        - Overall accuracy
        - Macro & weighted precision, recall, and F1
        - Per-class metrics (TP, FP, FN, TN, precision, recall, F1, support)
        - 38x38 confusion matrix
        - Confidence distribution statistics
        - Binned reliability & Expected Calibration Error (ECE)
        """
        if not dataset:
            raise ValueError("Cannot evaluate an empty dataset.")

        num_samples = len(dataset)
        y_true = np.zeros(num_samples, dtype=np.int64)
        y_pred = np.zeros(num_samples, dtype=np.int64)
        confidences = np.zeros(num_samples, dtype=np.float64)
        latencies_ms = np.zeros(num_samples, dtype=np.float64)

        t_eval_start = time.perf_counter()

        for idx, sample in enumerate(dataset):
            img_path = sample["image_path"]
            y_true[idx] = sample["true_label_idx"]

            # Run inference via DiseaseDetector service
            res = self.detector.predict(
                image_path=img_path,
                preprocessing_mode=preprocessing_mode,
                enable_tta=enable_tta
            )

            # Determine predicted class index
            top_prediction = res["top_predictions"][0]
            pred_class_name = top_prediction["class_name"]
            y_pred[idx] = self.class_to_idx.get(pred_class_name, -1)
            confidences[idx] = float(top_prediction["confidence"])
            latencies_ms[idx] = float(res.get("latency_ms", 0.0))

        total_eval_time_s = time.perf_counter() - t_eval_start

        # -------------------------------------------------------------
        # 1. Confusion Matrix (38 x 38)
        # -------------------------------------------------------------
        cm = np.zeros((self.num_classes, self.num_classes), dtype=np.int64)
        for t, p in zip(y_true, y_pred):
            if 0 <= t < self.num_classes and 0 <= p < self.num_classes:
                cm[t, p] += 1

        # -------------------------------------------------------------
        # 2. Per-Class Precision, Recall, F1, Support
        # -------------------------------------------------------------
        per_class_metrics: List[Dict[str, Any]] = []
        tp_sum = 0
        total_support = num_samples

        precisions = np.zeros(self.num_classes, dtype=np.float64)
        recalls = np.zeros(self.num_classes, dtype=np.float64)
        f1_scores = np.zeros(self.num_classes, dtype=np.float64)
        supports = np.zeros(self.num_classes, dtype=np.int64)

        for c in range(self.num_classes):
            tp = int(cm[c, c])
            fp = int(np.sum(cm[:, c]) - tp)
            fn = int(np.sum(cm[c, :]) - tp)
            tn = int(np.sum(cm) - (tp + fp + fn))
            support = int(np.sum(cm[c, :]))

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2.0 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            precisions[c] = prec
            recalls[c] = rec
            f1_scores[c] = f1
            supports[c] = support
            tp_sum += tp

            per_class_metrics.append({
                "class_index": c,
                "class_name": self.classes[c],
                "precision": round(float(prec), 4),
                "recall": round(float(rec), 4),
                "f1_score": round(float(f1), 4),
                "support": support,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn
            })

        # -------------------------------------------------------------
        # 3. Overall, Macro, and Weighted Averages
        # -------------------------------------------------------------
        overall_accuracy = float(tp_sum / total_support) if total_support > 0 else 0.0

        # Classes present in ground truth
        active_mask = supports > 0
        num_active = int(np.sum(active_mask))

        macro_precision = float(np.mean(precisions[active_mask])) if num_active > 0 else 0.0
        macro_recall = float(np.mean(recalls[active_mask])) if num_active > 0 else 0.0
        macro_f1 = float(np.mean(f1_scores[active_mask])) if num_active > 0 else 0.0

        weighted_precision = float(np.sum(precisions * supports) / total_support) if total_support > 0 else 0.0
        weighted_recall = float(np.sum(recalls * supports) / total_support) if total_support > 0 else 0.0
        weighted_f1 = float(np.sum(f1_scores * supports) / total_support) if total_support > 0 else 0.0

        # -------------------------------------------------------------
        # 4. Confidence Distribution Statistics
        # -------------------------------------------------------------
        conf_mean = float(np.mean(confidences))
        conf_std = float(np.std(confidences))
        conf_min = float(np.min(confidences))
        conf_max = float(np.max(confidences))
        p25, p50, p75 = [float(x) for x in np.percentile(confidences, [25, 50, 75])]

        # Histogram of confidences across 10 bins: [0.0-0.1, ..., 0.9-1.0]
        bin_edges = np.linspace(0.0, 1.0, 11)
        hist_counts, _ = np.histogram(confidences, bins=bin_edges)
        confidence_histogram = {
            f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}": int(hist_counts[i])
            for i in range(10)
        }

        # -------------------------------------------------------------
        # 5. Calibration: Expected Calibration Error (ECE) & Reliability
        # -------------------------------------------------------------
        is_correct = (y_true == y_pred).astype(np.float64)
        ece = 0.0
        calibration_bins: List[Dict[str, Any]] = []

        for i in range(10):
            low, high = bin_edges[i], bin_edges[i+1]
            if i == 9:
                in_bin = (confidences >= low) & (confidences <= high)
            else:
                in_bin = (confidences >= low) & (confidences < high)

            bin_size = int(np.sum(in_bin))
            if bin_size > 0:
                bin_acc = float(np.mean(is_correct[in_bin]))
                bin_conf = float(np.mean(confidences[in_bin]))
                bin_error = abs(bin_acc - bin_conf)
                ece += (bin_size / total_support) * bin_error
            else:
                bin_acc = 0.0
                bin_conf = 0.0
                bin_error = 0.0

            calibration_bins.append({
                "bin_range": f"{low:.1f}-{high:.1f}",
                "sample_count": bin_size,
                "accuracy": round(bin_acc, 4),
                "avg_confidence": round(bin_conf, 4),
                "calibration_gap": round(bin_error, 4)
            })

        # -------------------------------------------------------------
        # 6. Latency Benchmarks
        # -------------------------------------------------------------
        avg_latency_ms = float(np.mean(latencies_ms))
        p50_latency_ms = float(np.median(latencies_ms))
        p95_latency_ms = float(np.percentile(latencies_ms, 95))

        return {
            "metadata": {
                "num_samples": num_samples,
                "num_classes": self.num_classes,
                "active_classes": num_active,
                "preprocessing_mode": preprocessing_mode,
                "tta_enabled": enable_tta,
                "total_evaluation_time_sec": round(total_eval_time_s, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "evaluation_note": "Evaluated against supplied labeled dataset. Metadata val_accuracy represents training artifact, not real-world deployment accuracy."
            },
            "overall_metrics": {
                "overall_accuracy": round(overall_accuracy, 4),
                "macro_precision": round(macro_precision, 4),
                "macro_recall": round(macro_recall, 4),
                "macro_f1": round(macro_f1, 4),
                "weighted_precision": round(weighted_precision, 4),
                "weighted_recall": round(weighted_recall, 4),
                "weighted_f1": round(weighted_f1, 4),
                "expected_calibration_error": round(float(ece), 4)
            },
            "confidence_distribution": {
                "mean": round(conf_mean, 4),
                "std": round(conf_std, 4),
                "min": round(conf_min, 4),
                "p25": round(p25, 4),
                "median": round(p50, 4),
                "p75": round(p75, 4),
                "max": round(conf_max, 4),
                "histogram_10_bins": confidence_histogram
            },
            "calibration_curve": calibration_bins,
            "latency": {
                "average_ms": round(avg_latency_ms, 2),
                "p50_ms": round(p50_latency_ms, 2),
                "p95_ms": round(p95_latency_ms, 2)
            },
            "per_class_metrics": per_class_metrics,
            "confusion_matrix": cm.tolist()
        }

    def export_json(self, results: Dict[str, Any], output_path: Union[str, Path]) -> None:
        """Exports evaluation results to a clean JSON file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    def export_per_class_csv(self, results: Dict[str, Any], output_path: Union[str, Path]) -> None:
        """Exports per-class metrics to a tabular CSV file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        per_class = results.get("per_class_metrics", [])
        if not per_class:
            return

        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "class_index", "class_name", "precision", "recall", "f1_score",
                "support", "tp", "fp", "fn", "tn"
            ])
            writer.writeheader()
            for row in per_class:
                writer.writerow(row)

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Displays human-readable evaluation summary tables in console."""
        meta = results["metadata"]
        om = results["overall_metrics"]
        conf = results["confidence_distribution"]
        lat = results["latency"]

        print("\n" + "=" * 70)
        print("          AGRONEX ONNX MODEL QUANTITATIVE EVALUATION REPORT          ")
        print("=" * 70)
        print(f"Dataset Size:           {meta['num_samples']} labeled images across {meta['active_classes']} active classes")
        print(f"Preprocessing Strategy: {meta['preprocessing_mode'].upper()} (TTA={'ON' if meta['tta_enabled'] else 'OFF'})")
        print(f"Evaluation Completed:   {meta['timestamp']} ({meta['total_evaluation_time_sec']}s)")
        print("-" * 70)
        print(f"Overall Accuracy:       {om['overall_accuracy'] * 100:.2f}%")
        print(f"Macro Precision:        {om['macro_precision'] * 100:.2f}%")
        print(f"Macro Recall:           {om['macro_recall'] * 100:.2f}%")
        print(f"Macro F1 Score:         {om['macro_f1'] * 100:.2f}%")
        print(f"Weighted F1 Score:      {om['weighted_f1'] * 100:.2f}%")
        print(f"Expected Calib Error:   {om['expected_calibration_error'] * 100:.2f}% (ECE)")
        print(f"Average Latency:        {lat['average_ms']:.2f} ms/image (p95: {lat['p95_ms']:.2f} ms)")
        print("-" * 70)
        print(f"Confidence Stats:       Mean: {conf['mean']*100:.1f}% | Median: {conf['median']*100:.1f}% | Min: {conf['min']*100:.1f}% | Max: {conf['max']*100:.1f}%")
        print("=" * 70)

        # Print top classes by support
        print(f"\n{'Index':<5} | {'Class Name':<38} | {'Prec':<7} | {'Rec':<7} | {'F1':<7} | {'Support'}")
        print("-" * 75)
        per_class = sorted(results["per_class_metrics"], key=lambda x: x["support"], reverse=True)
        for c in per_class[:10]:
            print(f"{c['class_index']:<5} | {c['class_name'][:38]:<38} | {c['precision']*100:5.1f}% | {c['recall']*100:5.1f}% | {c['f1_score']*100:5.1f}% | {c['support']}")
        if len(per_class) > 10:
            print(f"... and {len(per_class) - 10} additional classes.")
        print("=" * 75 + "\n")
