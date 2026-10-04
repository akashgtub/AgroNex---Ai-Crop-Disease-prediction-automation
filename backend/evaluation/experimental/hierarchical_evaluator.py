"""
AgroNex Hierarchical Crop -> Disease Experimental Evaluator
Evaluates the impact of simulated hierarchical constraints on the existing EfficientNetV2-S ONNX model.
Compares:
  1. Baseline Unrestricted 38-class classification
  2. Hierarchical Predicted-Crop Constrained classification (Probabilistic Sum Aggregation)
  3. Hierarchical Oracle-Crop Constrained classification (Ground-Truth Crop Known / Theoretical Bound)
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import onnxruntime as ort
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from evaluation.experimental.crop_mapping import CropTaxonomy


class HierarchicalEvaluator:
    """Evaluates hierarchical crop-to-disease inference strategies."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        classes_path: Optional[Path] = None,
    ):
        self.backend_dir = Path(__file__).resolve().parent.parent.parent
        self.model_path = model_path or (self.backend_dir / "models" / "efficientnet_v2_s_best.onnx")
        self.classes_path = classes_path or (self.backend_dir / "models" / "classes.json")

        self.taxonomy = CropTaxonomy(self.classes_path)
        self.classes = self.taxonomy.classes
        self.num_classes = self.taxonomy.num_classes
        self.class_to_idx = self.taxonomy.class_to_idx

        # Setup ONNX session
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.intra_op_num_threads = 4
        self.session = ort.InferenceSession(
            str(self.model_path), sess_options=session_options, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        # Normalization constants (ImageNet)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

    def preprocess_image(self, img_path: Path) -> np.ndarray:
        """Preprocesses image using direct squish resize to 224x224."""
        with Image.open(img_path) as img:
            img_rgb = img.convert("RGB")
            resized = img_rgb.resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.asarray(resized, dtype=np.float32) / 255.0
            normalized = (arr - self.mean) / self.std
            chw = np.transpose(normalized, (2, 0, 1))
            return np.expand_dims(chw, axis=0)

    @staticmethod
    def stable_softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits, axis=-1, keepdims=True)
        exp = np.exp(shifted)
        return exp / np.sum(exp, axis=-1, keepdims=True)

    @staticmethod
    def calculate_ece(confidences: np.ndarray, correctness: np.ndarray, num_bins: int = 10) -> float:
        """Computes Expected Calibration Error."""
        bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
        ece = 0.0
        n_samples = len(confidences)
        for i in range(num_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]
            mask = (confidences >= bin_lower) & (confidences < bin_upper if i < num_bins - 1 else confidences <= bin_upper)
            bin_size = np.sum(mask)
            if bin_size > 0:
                bin_acc = np.mean(correctness[mask])
                bin_conf = np.mean(confidences[mask])
                ece += (bin_size / n_samples) * np.abs(bin_acc - bin_conf)
        return float(ece)

    def load_manifest(self, manifest_path: Path) -> List[Dict[str, Any]]:
        """Loads and validates manifest CSV."""
        base_dir = manifest_path.parent
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            samples = []
            for row in reader:
                rel_path = row["image_path"]
                full_path = (base_dir / rel_path).resolve()
                label = row["label"]
                if not full_path.exists():
                    continue
                true_idx = self.class_to_idx[label]
                true_crop = self.taxonomy.get_crop(true_idx)
                samples.append({
                    "image_path": full_path,
                    "true_label": label,
                    "true_index": true_idx,
                    "true_crop": true_crop,
                    "mapping_type": row.get("mapping_type", "UNKNOWN"),
                    "plantdoc_class": row.get("plantdoc_class", label)
                })
        return samples

    def run_experiment(self, manifest_path: Path) -> Dict[str, Any]:
        """Runs the complete comparative hierarchical experiment."""
        samples = self.load_manifest(manifest_path)
        if not samples:
            raise ValueError(f"No valid samples loaded from {manifest_path}")

        y_true = np.array([s["true_index"] for s in samples], dtype=int)
        true_crops = [s["true_crop"] for s in samples]
        n_samples = len(samples)

        raw_probs_list = []
        # Run forward pass for all images
        for s in samples:
            tensor = self.preprocess_image(s["image_path"])
            logits = self.session.run([self.output_name], {self.input_name: tensor})[0]
            probs = self.stable_softmax(logits)[0]
            raw_probs_list.append(probs)

        # -------------------------------------------------------------
        # Strategy A: Baseline Unrestricted
        # -------------------------------------------------------------
        base_preds = np.array([int(np.argmax(p)) for p in raw_probs_list], dtype=int)
        base_confs = np.array([float(p[base_preds[i]]) for i, p in enumerate(raw_probs_list)])
        base_pred_crops = [self.taxonomy.get_crop(idx) for idx in base_preds]

        # -------------------------------------------------------------
        # Strategy B: Hierarchical Predicted Crop (Sum Aggregation)
        # -------------------------------------------------------------
        hier_preds = []
        hier_confs = []
        hier_pred_crops = []

        for p in raw_probs_list:
            crop_probs = self.taxonomy.aggregate_crop_probabilities(p)
            best_crop = max(crop_probs.keys(), key=lambda c: crop_probs[c])
            best_disease_idx, best_disease_conf, _ = self.taxonomy.renormalize_for_crop(p, best_crop)
            hier_preds.append(best_disease_idx)
            hier_confs.append(best_disease_conf)
            hier_pred_crops.append(best_crop)

        hier_preds = np.array(hier_preds, dtype=int)
        hier_confs = np.array(hier_confs)

        # -------------------------------------------------------------
        # Strategy C: Oracle Crop (Ground-Truth Crop Known)
        # -------------------------------------------------------------
        oracle_preds = []
        oracle_confs = []

        for i, p in enumerate(raw_probs_list):
            oracle_crop = true_crops[i]
            best_disease_idx, best_disease_conf, _ = self.taxonomy.renormalize_for_crop(p, oracle_crop)
            oracle_preds.append(best_disease_idx)
            oracle_confs.append(best_disease_conf)

        oracle_preds = np.array(oracle_preds, dtype=int)
        oracle_confs = np.array(oracle_confs)

        # Compute metrics for each strategy
        def evaluate_strategy(preds: np.ndarray, confs: np.ndarray, pred_crops: List[str], name: str) -> Dict[str, Any]:
            acc = float(accuracy_score(y_true, preds))
            active_labels = sorted(list(set(y_true)))

            p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
                y_true, preds, labels=active_labels, average="macro", zero_division=0
            )
            p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(
                y_true, preds, labels=active_labels, average="weighted", zero_division=0
            )

            cm = confusion_matrix(y_true, preds, labels=list(range(self.num_classes))).tolist()
            correctness = (y_true == preds).astype(int)
            ece = self.calculate_ece(confs, correctness)

            # Cross-crop vs intra-crop error analysis
            cross_crop_errors = 0
            intra_crop_errors = 0
            for i in range(n_samples):
                if preds[i] != y_true[i]:
                    if pred_crops[i] != true_crops[i]:
                        cross_crop_errors += 1
                    else:
                        intra_crop_errors += 1

            # Sink counts
            scorch_fps = int(np.sum((preds == self.class_to_idx["Strawberry___Leaf_scorch"]) & (y_true != self.class_to_idx["Strawberry___Leaf_scorch"])))
            pepper_healthy_fps = int(np.sum((preds == self.class_to_idx["Pepper,_bell___healthy"]) & (y_true != self.class_to_idx["Pepper,_bell___healthy"])))
            tlb_fps = int(np.sum((preds == self.class_to_idx["Tomato___Late_blight"]) & (y_true != self.class_to_idx["Tomato___Late_blight"])))

            crop_acc = float(np.mean([pred_crops[i] == true_crops[i] for i in range(n_samples)]))

            return {
                "strategy": name,
                "overall_accuracy": acc,
                "crop_accuracy": crop_acc,
                "macro_precision": float(p_macro),
                "macro_recall": float(r_macro),
                "macro_f1": float(f1_macro),
                "weighted_precision": float(p_wt),
                "weighted_recall": float(r_wt),
                "weighted_f1": float(f1_wt),
                "expected_calibration_error": ece,
                "mean_confidence": float(np.mean(confs)),
                "median_confidence": float(np.median(confs)),
                "total_errors": int(n_samples - np.sum(correctness)),
                "cross_crop_errors": cross_crop_errors,
                "intra_crop_errors": intra_crop_errors,
                "strawberry_scorch_fps": scorch_fps,
                "pepper_healthy_fps": pepper_healthy_fps,
                "tomato_late_blight_fps": tlb_fps,
                "confusion_matrix": cm
            }

        base_metrics = evaluate_strategy(base_preds, base_confs, base_pred_crops, "Baseline Unrestricted (38-class flat)")
        hier_metrics = evaluate_strategy(hier_preds, hier_confs, hier_pred_crops, "Hierarchical (Predicted Crop via Sum Aggregation)")
        oracle_metrics = evaluate_strategy(oracle_preds, oracle_confs, true_crops, "Hierarchical Oracle (Ground-Truth Crop Known)")

        return {
            "dataset_samples": n_samples,
            "manifest_path": str(manifest_path),
            "baseline": base_metrics,
            "hierarchical_predicted": hier_metrics,
            "hierarchical_oracle": oracle_metrics
        }

    def print_comparison_report(self, results: Dict[str, Any]):
        """Prints a human-readable comparison report."""
        b = results["baseline"]
        h = results["hierarchical_predicted"]
        o = results["hierarchical_oracle"]
        total = results["dataset_samples"]

        print("\n" + "=" * 95)
        print("          AGRONEX PHASE 4B: HIERARCHICAL CROP -> DISEASE EXPERIMENT REPORT           ")
        print("=" * 95)
        print(f"Dataset Size:           {total} labeled images (PlantDoc official test split)")
        print(f"Total Disease Classes:  {self.num_classes} classes across {self.taxonomy.num_crops} botanical crop species")
        print("-" * 95)

        header = f"{'Metric':<32} | {'A. Baseline (Flat)':<18} | {'B. Hierarchical (Pred)':<22} | {'C. Oracle Crop'}"
        print(header)
        print("-" * 95)

        def row(name, va, vb, vc, pct=False):
            if pct:
                print(f"{name:<32} | {va*100:6.2f}%            | {vb*100:6.2f}%                | {vc*100:6.2f}%")
            else:
                print(f"{name:<32} | {str(va):<18} | {str(vb):<22} | {str(vc)}")

        row("Crop Accuracy", b["crop_accuracy"], h["crop_accuracy"], o["crop_accuracy"], pct=True)
        row("Disease Diagnosis Accuracy", b["overall_accuracy"], h["overall_accuracy"], o["overall_accuracy"], pct=True)
        row("Macro F1 Score", b["macro_f1"], h["macro_f1"], o["macro_f1"], pct=True)
        row("Weighted F1 Score", b["weighted_f1"], h["weighted_f1"], o["weighted_f1"], pct=True)
        row("Expected Calib Error (ECE)", b["expected_calibration_error"], h["expected_calibration_error"], o["expected_calibration_error"], pct=True)
        row("Mean Confidence", b["mean_confidence"], h["mean_confidence"], o["mean_confidence"], pct=True)
        print("-" * 95)
        row("Total Diagnosis Errors", b["total_errors"], h["total_errors"], o["total_errors"])
        row("Cross-Crop Errors", b["cross_crop_errors"], h["cross_crop_errors"], o["cross_crop_errors"])
        row("Intra-Crop Errors", b["intra_crop_errors"], h["intra_crop_errors"], o["intra_crop_errors"])
        print("-" * 95)
        row("Strawberry Scorch FPs (Sink 1)", b["strawberry_scorch_fps"], h["strawberry_scorch_fps"], o["strawberry_scorch_fps"])
        row("Pepper Healthy FPs (Sink 2)", b["pepper_healthy_fps"], h["pepper_healthy_fps"], o["pepper_healthy_fps"])
        row("Tomato Late Blight FPs (Sink 3)", b["tomato_late_blight_fps"], h["tomato_late_blight_fps"], o["tomato_late_blight_fps"])
        print("=" * 95)


def main():
    parser = argparse.ArgumentParser(description="AgroNex Hierarchical Crop-to-Disease Experiment")
    parser.add_argument(
        "--data-path", "-d",
        type=str,
        default="backend/evaluation/manifests/plantdoc_test_manifest.csv",
        help="Path to labeled evaluation manifest CSV."
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="backend/evaluation/results/hierarchical_experiment_results.json",
        help="Path to export experimental JSON results."
    )
    args = parser.parse_args()

    evaluator = HierarchicalEvaluator()
    manifest_path = Path(args.data_path)
    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found: {manifest_path}")
        sys.exit(1)

    print(f"[INFO] Running Hierarchical Experiment on: {manifest_path}")
    results = evaluator.run_experiment(manifest_path)
    evaluator.print_comparison_report(results)

    # Export results
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[INFO] Results exported to: {out_path}\n")


if __name__ == "__main__":
    main()
