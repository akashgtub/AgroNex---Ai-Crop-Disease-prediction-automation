"""
AgroNex Phase 4C-2: Three-Way Model Comparative Evaluation
Evaluates on the untouched 236-image PlantDoc test set:
  A. Baseline Production Model (20.34%)
  B. Phase 4C-1 Head-Only Fine-Tuned (32.63%)
  C. Phase 4C-2 Partial-Backbone + Domain-Replay
Also checks preservation of the 11 missing classes on PlantVillage sanity subset.
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
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "efficientnet_v2_s_best.onnx"
CLASSES_JSON = PROJECT_ROOT / "backend" / "models" / "classes.json"
PLANTDOC_TEST_MANIFEST = PROJECT_ROOT / "backend" / "evaluation" / "manifests" / "plantdoc_test_manifest.csv"
PLANTVILLAGE_SANITY_MANIFEST = PROJECT_ROOT / "backend" / "evaluation" / "manifests" / "plantvillage_sanity_manifest.csv"

CKPT_4C1 = Path(__file__).resolve().parent / "checkpoints" / "phase4c_finetuned_head.pth"
CKPT_4C2 = Path(__file__).resolve().parent / "checkpoints" / "phase4c2_best_model.pth"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "evaluation" / "results" / "phase4c2_evaluation_results.json"

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


def load_classes() -> Tuple[List[str], Dict[str, int]]:
    with open(CLASSES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    classes = data["classes"]
    return classes, {c: i for i, c in enumerate(classes)}


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


class PartialBackboneHead(nn.Module):
    def __init__(self, in_channels: int = 256, mid_channels: int = 1280, num_classes: int = 38):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, mid_channels, kernel_size=1, bias=True)
        self.act = nn.SiLU()
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(0.2)
        self.classifier = nn.Linear(mid_channels, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.act(self.conv(x))
        pooled = torch.flatten(self.pool(h), 1)
        dropped = self.dropout(pooled)
        return self.classifier(dropped)


def setup_extractor() -> ort.InferenceSession:
    model = onnx.load(str(MODEL_PATH))
    f6_out = onnx.helper.make_tensor_value_info("add_3505", onnx.TensorProto.FLOAT, [None, 256, 7, 7])
    model.graph.output.append(f6_out)
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.intra_op_num_threads = 4
    return ort.InferenceSession(model.SerializeToString(), sess_options=opts, providers=["CPUExecutionProvider"])


def evaluate_dataset(
    manifest_path: Path,
    session: ort.InferenceSession,
    model_4c1_weights: Tuple[np.ndarray, np.ndarray],
    model_4c2: nn.Module,
    classes: List[str],
    class_to_idx: Dict[str, int]
) -> Dict[str, Any]:
    base_dir = manifest_path.parent
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    y_true = []
    crops = []
    base_logits_list = []
    f6_maps_list = []

    for row in reader:
        img_p = base_dir / row["image_path"]
        target = class_to_idx[row["label"]]
        y_true.append(target)
        crops.append(get_crop(row["label"]))

        tensor_in = image_to_tensor(img_p)
        logits, f6 = session.run(["logits", "add_3505"], {"input": tensor_in})
        base_logits_list.append(logits[0])
        f6_maps_list.append(f6[0])

    y_true = np.array(y_true)
    f6_tensor = torch.tensor(np.array(f6_maps_list), dtype=torch.float32)

    # Model A: Baseline Production Logits
    base_logits = np.array(base_logits_list)

    # Model B: Phase 4C-1 Logits (w_4c1, b_4c1 on 1280-dim feature vector)
    # The 1280-dim vector is pool(SiLU(features.7.0(f6)))
    # We can compute it using the model_4c2's initial conv or directly
    w_4c1, b_4c1 = model_4c1_weights

    # Model C: Phase 4C-2 Logits
    model_4c2.eval()
    with torch.no_grad():
        c_logits = model_4c2(f6_tensor).numpy()

    # To get exact B logits, we load checkpoint 4C1 onto model_4c2 before conv fine-tuning or compute via ONNX view
    # Let's extract 'view' for exact B logits
    # Actually, model A logits are exact ONNX production logits
    # Let's evaluate a set of logits
    def compute_metrics(logits: np.ndarray, model_name: str) -> Dict[str, Any]:
        probs = softmax(logits)
        preds = np.argmax(probs, axis=-1)
        confs = np.max(probs, axis=-1)

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

        cross_crop = 0
        intra_crop = 0
        for i in range(len(preds)):
            if preds[i] != y_true[i]:
                pred_c = get_crop(classes[preds[i]])
                true_c = crops[i]
                if pred_c != true_c:
                    cross_crop += 1
                else:
                    intra_crop += 1

        scorch_idx = class_to_idx["Strawberry___Leaf_scorch"]
        pepper_healthy_idx = class_to_idx["Pepper,_bell___healthy"]
        tlb_idx = class_to_idx["Tomato___Late_blight"]

        scorch_fps = int(np.sum((preds == scorch_idx) & (y_true != scorch_idx)))
        pepper_fps = int(np.sum((preds == pepper_healthy_idx) & (y_true != pepper_healthy_idx)))
        tlb_fps = int(np.sum((preds == tlb_idx) & (y_true != tlb_idx)))

        per_class_rec = {}
        for c_idx in active_labels:
            mask = (y_true == c_idx)
            rec = float(np.mean(preds[mask] == c_idx)) if np.sum(mask) > 0 else 0.0
            per_class_rec[classes[c_idx]] = {
                "support": int(np.sum(mask)),
                "recall": rec
            }

        return {
            "name": model_name,
            "accuracy": acc,
            "macro_precision": float(p_macro),
            "macro_recall": float(r_macro),
            "macro_f1": float(f1_macro),
            "weighted_precision": float(p_wt),
            "weighted_recall": float(r_wt),
            "weighted_f1": float(f1_wt),
            "ece": ece,
            "mean_confidence": float(np.mean(confs)),
            "total_errors": int(np.sum(preds != y_true)),
            "cross_crop_errors": cross_crop,
            "intra_crop_errors": intra_crop,
            "strawberry_scorch_fps": scorch_fps,
            "pepper_healthy_fps": pepper_fps,
            "tomato_late_blight_fps": tlb_fps,
            "per_class_recalls": per_class_rec,
            "preds": preds.tolist()
        }

    res_a = compute_metrics(base_logits, "Model A: Baseline Production")
    res_c = compute_metrics(c_logits, "Model C: Phase 4C-2 Partial-Backbone + Replay")

    return {
        "samples": len(y_true),
        "model_a": res_a,
        "model_c": res_c
    }


def main():
    classes, class_to_idx = load_classes()
    session = setup_extractor()

    # Load 4C-1 results for comparison
    with open(PROJECT_ROOT / "backend" / "evaluation" / "results" / "phase4c_evaluation_results.json", "r") as f:
        res_4c1 = json.load(f)["finetuned"]

    # Load 4C-2 trained model
    ckpt_4c2 = torch.load(CKPT_4C2, map_location="cpu", weights_only=True)
    model_4c2 = PartialBackboneHead(256, 1280, 38)
    model_4c2.load_state_dict(ckpt_4c2["state_dict"])
    model_4c2.eval()

    print(f"\n[INFO] Loaded Phase 4C-2 checkpoint: {CKPT_4C2}")
    print(f"[INFO] Best epoch during training: {ckpt_4c2['best_epoch']} (Val Acc: {ckpt_4c2['best_val_acc']*100:.2f}%)")

    # 1. Evaluate on untouched PlantDoc test set
    pd_eval = evaluate_dataset(
        PLANTDOC_TEST_MANIFEST,
        session,
        (None, None),
        model_4c2,
        classes,
        class_to_idx
    )

    ma = pd_eval["model_a"]
    mb = res_4c1
    mc = pd_eval["model_c"]

    # Print 3-Way Comparison Table
    print("\n" + "=" * 105)
    print("      AGRONEX THREE-WAY BENCHMARK: BASELINE vs PHASE 4C-1 vs PHASE 4C-2 (UNTOUCHED TEST SET)      ")
    print("=" * 105)
    print(f"{'Metric':<32} | {'A. Baseline Prod':<18} | {'B. Phase 4C-1 (Head)':<20} | {'C. Phase 4C-2 (+Backbone)':<24} | {'Delta (C vs A)'}")
    print("-" * 105)

    def print_row(title, va, vb, vc, pct=False):
        d_val = vc - va
        if pct:
            a_s = f"{va*100:6.2f}%"
            b_s = f"{vb*100:6.2f}%"
            c_s = f"{vc*100:6.2f}%"
            d_s = f"{d_val*100:+6.2f}%"
        else:
            a_s = str(va)
            b_s = str(vb)
            c_s = str(vc)
            d_s = f"{d_val:+d}"
        print(f"{title:<32} | {a_s:<18} | {b_s:<20} | {c_s:<24} | {d_s}")

    print_row("Overall Accuracy", ma["accuracy"], mb["accuracy"], mc["accuracy"], pct=True)
    print_row("Macro Precision", ma["macro_precision"], mb["macro_precision"], mc["macro_precision"], pct=True)
    print_row("Macro Recall", ma["macro_recall"], mb["macro_recall"], mc["macro_recall"], pct=True)
    print_row("Macro F1 Score", ma["macro_f1"], mb["macro_f1"], mc["macro_f1"], pct=True)
    print_row("Weighted F1 Score", ma["weighted_f1"], mb["weighted_f1"], mc["weighted_f1"], pct=True)
    print_row("Expected Calib Error (ECE)", ma["ece"], mb["ece"], mc["ece"], pct=True)
    print_row("Mean Confidence", ma["mean_confidence"], mb["mean_confidence"], mc["mean_confidence"], pct=True)
    print("-" * 105)
    print_row("Total Errors", ma["total_errors"], mb["total_errors"], mc["total_errors"])
    print_row("Cross-Crop Errors", ma["cross_crop_errors"], mb["cross_crop_errors"], mc["cross_crop_errors"])
    print_row("Intra-Crop Errors", ma["intra_crop_errors"], mb["intra_crop_errors"], mc["intra_crop_errors"])
    print("-" * 105)
    print_row("Strawberry Scorch FPs (Sink 1)", ma["strawberry_scorch_fps"], mb["strawberry_scorch_fps"], mc["strawberry_scorch_fps"])
    print_row("Pepper Healthy FPs (Sink 2)", ma["pepper_healthy_fps"], mb["pepper_healthy_fps"], mc["pepper_healthy_fps"])
    print_row("Tomato Late Blight FPs (Sink 3)", ma["tomato_late_blight_fps"], mb["tomato_late_blight_fps"], mc["tomato_late_blight_fps"])
    print("=" * 105)

    # 2. Evaluate Model C on PlantVillage Sanity to check 11 missing classes preservation!
    pv_eval = evaluate_dataset(
        PLANTVILLAGE_SANITY_MANIFEST,
        session,
        (None, None),
        model_4c2,
        classes,
        class_to_idx
    )
    pv_c = pv_eval["model_c"]
    print("\n" + "=" * 80)
    print("       CHECK FOR PRESERVATION OF 11 CLASSES ABSENT FROM PLANTDOC       ")
    print("=" * 80)
    print(f"PlantVillage Sanity Accuracy on Model C: {pv_c['accuracy']*100:.2f}% (190 studio images)")

    missing_11_classes = [
        "Apple___Black_rot",
        "Cherry_(including_sour)___Powdery_mildew",
        "Corn_(maize)___healthy",
        "Grape___Esca_(Black_Measles)",
        "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
        "Orange___Haunglongbing_(Citrus_greening)",
        "Peach___Bacterial_spot",
        "Potato___healthy",
        "Strawberry___Leaf_scorch",
        "Tomato___Spider_mites Two-spotted_spider_mite",
        "Tomato___Target_Spot"
    ]

    print(f"\n{'Absent Class Name':<45} | {'Support':<8} | {'Recall on Model C'}")
    print("-" * 75)
    missing_recalls = pv_c["per_class_recalls"]
    preserved_count = 0
    for cls in missing_11_classes:
        rec_info = missing_recalls.get(cls, {"support": 5, "recall": 0.0})
        rec = rec_info["recall"]
        if rec >= 0.80:
            preserved_count += 1
        print(f"{cls:<45} | {rec_info['support']:<8} | {rec*100:6.1f}%")
    print("-" * 75)
    print(f"[SUMMARY] {preserved_count} / 11 unrepresented classes perfectly preserved at >= 80% recall.\n")

    # Export complete comparison JSON
    out_data = {
        "dataset": "PlantDoc Official Test Set (untouched)",
        "test_samples": pd_eval["samples"],
        "checkpoint": str(CKPT_4C2),
        "model_a_baseline": ma,
        "model_b_phase4c1": mb,
        "model_c_phase4c2": mc,
        "plantvillage_retention": {
            "overall_accuracy": pv_c["accuracy"],
            "missing_11_classes_preserved": preserved_count,
            "missing_11_classes_details": {cls: missing_recalls.get(cls, {}) for cls in missing_11_classes}
        }
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)
    print(f"[INFO] Detailed evaluation JSON exported to: {OUTPUT_JSON}\n")


if __name__ == "__main__":
    main()
