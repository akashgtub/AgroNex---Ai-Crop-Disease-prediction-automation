"""
AgroNex Phase 4C: Experimental Evaluation Script
Evaluates the fine-tuned classification head against the untouched 236-image PlantDoc test set.
Produces complete side-by-side comparison against the baseline production model.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import onnx
from onnx import numpy_helper
import onnxruntime as ort
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "efficientnet_v2_s_best.onnx"
CLASSES_JSON = PROJECT_ROOT / "backend" / "models" / "classes.json"
TEST_MANIFEST = PROJECT_ROOT / "backend" / "evaluation" / "manifests" / "plantdoc_test_manifest.csv"
CHECKPOINT_PATH = Path(__file__).resolve().parent / "checkpoints" / "phase4c_finetuned_head.pth"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "evaluation" / "results" / "phase4c_evaluation_results.json"


def load_classes() -> Tuple[List[str], Dict[str, int]]:
    with open(CLASSES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    classes = data["classes"]
    return classes, {c: i for i, c in enumerate(classes)}


def setup_feature_extractor() -> Tuple[ort.InferenceSession, np.ndarray, np.ndarray]:
    model = onnx.load(str(MODEL_PATH))
    view_out = onnx.helper.make_tensor_value_info("view", onnx.TensorProto.FLOAT, [None, 1280])
    model.graph.output.append(view_out)

    session_opts = ort.SessionOptions()
    session_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session_opts.intra_op_num_threads = 4
    session = ort.InferenceSession(model.SerializeToString(), sess_options=session_opts, providers=["CPUExecutionProvider"])

    init_map = {init.name: numpy_helper.to_array(init) for init in model.graph.initializer}
    w_init = init_map["classifier.1.weight"].copy()  # (38, 1280)
    b_init = init_map["classifier.1.bias"].copy()    # (38,)
    return session, w_init, b_init


MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


def image_to_tensor(img_path: Path) -> np.ndarray:
    with Image.open(img_path) as img:
        img_rgb = img.convert("RGB")
        resized = img_rgb.resize((224, 224), Image.Resampling.BILINEAR)
        arr = np.asarray(resized, dtype=np.float32) / 255.0
        norm = (arr - MEAN) / STD
        chw = np.transpose(norm, (2, 0, 1))
        return np.expand_dims(chw, axis=0)


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def calculate_ece(confidences: np.ndarray, correctness: np.ndarray, num_bins: int = 10) -> float:
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


def get_crop(class_name: str) -> str:
    return class_name.split("___")[0]


def run_evaluation(checkpoint_file: Path) -> Dict[str, Any]:
    classes, class_to_idx = load_classes()
    num_classes = len(classes)

    session, w_base, b_base = setup_feature_extractor()

    # Load fine-tuned weights
    ckpt = torch.load(checkpoint_file, map_location="cpu", weights_only=True)
    state = ckpt["state_dict"]
    w_ft = state["linear.weight"].numpy()  # (38, 1280)
    b_ft = state["linear.bias"].numpy()    # (38,)

    # Load untouched test set
    base_dir = TEST_MANIFEST.parent
    with open(TEST_MANIFEST, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print(f"\n[INFO] Evaluating on untouched PlantDoc test set ({len(reader)} images)...")

    y_true = []
    features_list = []
    metadata = []

    for row in reader:
        img_path = base_dir / row["image_path"]
        target_idx = class_to_idx[row["label"]]
        y_true.append(target_idx)

        t_input = image_to_tensor(img_path)
        _, feat = session.run(["logits", "view"], {"input": t_input})
        features_list.append(feat[0])
        metadata.append({
            "image_path": str(img_path),
            "label": row["label"],
            "target_idx": target_idx,
            "crop": get_crop(row["label"])
        })

    X_test = np.array(features_list)  # (236, 1280)
    y_true = np.array(y_true)

    # 1. Baseline Logits
    base_logits = X_test @ w_base.T + b_base
    base_probs = softmax(base_logits)
    base_preds = np.argmax(base_probs, axis=-1)
    base_confs = np.max(base_probs, axis=-1)

    # 2. Fine-tuned Logits
    ft_logits = X_test @ w_ft.T + b_ft
    ft_probs = softmax(ft_logits)
    ft_preds = np.argmax(ft_probs, axis=-1)
    ft_confs = np.max(ft_probs, axis=-1)

    def evaluate_predictions(preds: np.ndarray, confs: np.ndarray, name: str) -> Dict[str, Any]:
        acc = float(accuracy_score(y_true, preds))
        active_labels = sorted(list(set(y_true)))

        p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
            y_true, preds, labels=active_labels, average="macro", zero_division=0
        )
        p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(
            y_true, preds, labels=active_labels, average="weighted", zero_division=0
        )

        correctness = (y_true == preds).astype(int)
        ece = calculate_ece(confs, correctness)

        cross_crop_errors = 0
        intra_crop_errors = 0
        for i in range(len(preds)):
            if preds[i] != y_true[i]:
                pred_crop = get_crop(classes[preds[i]])
                true_crop = metadata[i]["crop"]
                if pred_crop != true_crop:
                    cross_crop_errors += 1
                else:
                    intra_crop_errors += 1

        scorch_idx = class_to_idx["Strawberry___Leaf_scorch"]
        pepper_healthy_idx = class_to_idx["Pepper,_bell___healthy"]
        tlb_idx = class_to_idx["Tomato___Late_blight"]

        scorch_fps = int(np.sum((preds == scorch_idx) & (y_true != scorch_idx)))
        pepper_fps = int(np.sum((preds == pepper_healthy_idx) & (y_true != pepper_healthy_idx)))
        tlb_fps = int(np.sum((preds == tlb_idx) & (y_true != tlb_idx)))

        # Per-class recall for active classes
        per_class_recalls = {}
        for c_idx in active_labels:
            c_mask = (y_true == c_idx)
            rec = float(np.mean(preds[c_mask] == c_idx)) if np.sum(c_mask) > 0 else 0.0
            per_class_recalls[classes[c_idx]] = {
                "support": int(np.sum(c_mask)),
                "recall": rec
            }

        cm = confusion_matrix(y_true, preds, labels=list(range(num_classes))).tolist()

        return {
            "name": name,
            "accuracy": acc,
            "macro_precision": float(p_macro),
            "macro_recall": float(r_macro),
            "macro_f1": float(f1_macro),
            "weighted_precision": float(p_wt),
            "weighted_recall": float(r_wt),
            "weighted_f1": float(f1_wt),
            "ece": ece,
            "mean_confidence": float(np.mean(confs)),
            "median_confidence": float(np.median(confs)),
            "total_errors": int(np.sum(preds != y_true)),
            "cross_crop_errors": cross_crop_errors,
            "intra_crop_errors": intra_crop_errors,
            "strawberry_scorch_fps": scorch_fps,
            "pepper_healthy_fps": pepper_fps,
            "tomato_late_blight_fps": tlb_fps,
            "per_class_recalls": per_class_recalls,
            "confusion_matrix": cm
        }

    base_results = evaluate_predictions(base_preds, base_confs, "Baseline Production Model")
    ft_results = evaluate_predictions(ft_preds, ft_confs, "Phase 4C-1 Fine-Tuned Head")

    comparison = {
        "dataset": "PlantDoc Official Test Set (untouched)",
        "samples": len(y_true),
        "checkpoint": str(checkpoint_file),
        "baseline": base_results,
        "finetuned": ft_results,
        "delta": {
            "accuracy": ft_results["accuracy"] - base_results["accuracy"],
            "macro_f1": ft_results["macro_f1"] - base_results["macro_f1"],
            "weighted_f1": ft_results["weighted_f1"] - base_results["weighted_f1"],
            "ece": ft_results["ece"] - base_results["ece"],
            "cross_crop_errors": ft_results["cross_crop_errors"] - base_results["cross_crop_errors"],
            "strawberry_scorch_fps": ft_results["strawberry_scorch_fps"] - base_results["strawberry_scorch_fps"],
            "pepper_healthy_fps": ft_results["pepper_healthy_fps"] - base_results["pepper_healthy_fps"],
            "tomato_late_blight_fps": ft_results["tomato_late_blight_fps"] - base_results["tomato_late_blight_fps"],
        }
    }

    # Print summary table
    print("\n" + "=" * 90)
    print("            AGRONEX PHASE 4C-1: DOMAIN ADAPTATION BENCHMARK REPORT             ")
    print("=" * 90)
    print(f"Untouched Test Set Size: {len(y_true)} images across 27 classes")
    print("-" * 90)
    print(f"{'Metric':<32} | {'Baseline Production':<22} | {'Phase 4C-1 Fine-Tuned':<22} | {'Delta'}")
    print("-" * 90)

    def print_row(title, b_val, f_val, is_pct=False, invert_delta=False):
        d_val = f_val - b_val
        if is_pct:
            b_s = f"{b_val*100:6.2f}%"
            f_s = f"{f_val*100:6.2f}%"
            d_s = f"{d_val*100:+6.2f}%"
        else:
            b_s = str(b_val)
            f_s = str(f_val)
            d_s = f"{d_val:+d}"
        print(f"{title:<32} | {b_s:<22} | {f_s:<22} | {d_s}")

    print_row("Overall Accuracy", base_results["accuracy"], ft_results["accuracy"], is_pct=True)
    print_row("Macro Precision", base_results["macro_precision"], ft_results["macro_precision"], is_pct=True)
    print_row("Macro Recall", base_results["macro_recall"], ft_results["macro_recall"], is_pct=True)
    print_row("Macro F1 Score", base_results["macro_f1"], ft_results["macro_f1"], is_pct=True)
    print_row("Weighted F1 Score", base_results["weighted_f1"], ft_results["weighted_f1"], is_pct=True)
    print_row("Expected Calib Error (ECE)", base_results["ece"], ft_results["ece"], is_pct=True)
    print_row("Mean Confidence", base_results["mean_confidence"], ft_results["mean_confidence"], is_pct=True)
    print("-" * 90)
    print_row("Total Errors", base_results["total_errors"], ft_results["total_errors"])
    print_row("Cross-Crop Errors", base_results["cross_crop_errors"], ft_results["cross_crop_errors"])
    print_row("Intra-Crop Errors", base_results["intra_crop_errors"], ft_results["intra_crop_errors"])
    print("-" * 90)
    print_row("Strawberry Scorch FPs (Sink 1)", base_results["strawberry_scorch_fps"], ft_results["strawberry_scorch_fps"])
    print_row("Pepper Healthy FPs (Sink 2)", base_results["pepper_healthy_fps"], ft_results["pepper_healthy_fps"])
    print_row("Tomato Late Blight FPs (Sink 3)", base_results["tomato_late_blight_fps"], ft_results["tomato_late_blight_fps"])
    print("=" * 90)

    # Save output
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)
    print(f"[INFO] Detailed evaluation JSON exported to: {OUTPUT_JSON}\n")

    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, default=str(CHECKPOINT_PATH))
    args = parser.parse_args()
    run_evaluation(Path(args.checkpoint))
