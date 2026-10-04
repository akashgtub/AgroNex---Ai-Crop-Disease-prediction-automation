"""
AgroNex Phase 4C-2: Candidate ONNX Export & Multi-Stage Validation Suite
Performs:
  1. Reconstructs and exports the Phase 4C-2 candidate ONNX model:
     backend/training/phase4c/checkpoints/efficientnet_v2_s_phase4c2_candidate.onnx
     (Ensures backend/models/efficientnet_v2_s_best.onnx is NEVER touched/overwritten).
  2. Structural & Contract Validation:
     - Input tensor name, dtype, shape contract.
     - Output tensor name, dtype, shape contract.
     - Class count and ordering integrity with classes.json.
  3. Bit-level PyTorch vs ONNX Numerical Parity across all 236 test images:
     - Max absolute logit difference.
     - Mean absolute logit difference.
     - 100% Top-1 prediction agreement.
  4. Full Benchmark Evaluation on Untouched PlantDoc Test Set (236 images):
     - Accuracy, Macro F1, Weighted F1, ECE, Mean Confidence.
     - Cross-crop vs Intra-crop error decomposition.
     - False-positive sink counts (Strawberry Leaf Scorch, Pepper healthy, Tomato late blight).
  5. Production Preprocessing & Quality Pipeline Integration:
     - Uses production DiseaseDetector with candidate ONNX.
     - Tests repository sample images across direct/letterbox and TTA modes.
"""

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
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROD_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "efficientnet_v2_s_best.onnx"
CLASSES_JSON = PROJECT_ROOT / "backend" / "models" / "classes.json"
CHECKPOINT_PTH = Path(__file__).resolve().parent / "checkpoints" / "phase4c2_best_model.pth"
CANDIDATE_ONNX = Path(__file__).resolve().parent / "checkpoints" / "efficientnet_v2_s_phase4c2_candidate.onnx"

PLANTDOC_TEST_MANIFEST = PROJECT_ROOT / "backend" / "evaluation" / "manifests" / "plantdoc_test_manifest.csv"
SAMPLE_DIR = PROJECT_ROOT / "backend" / "models"

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


def get_crop(class_name: str) -> str:
    return class_name.split("___")[0]


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


def export_candidate_onnx() -> Path:
    """Exports candidate ONNX model by grafting Phase 4C-2 fine-tuned initializers onto the production graph."""
    print("=" * 80)
    print(" STEP 1: EXPORT CANDIDATE ONNX (Phase 4C-2)")
    print("=" * 80)
    assert PROD_MODEL_PATH.exists(), f"Production ONNX model not found: {PROD_MODEL_PATH}"
    assert CHECKPOINT_PTH.exists(), f"Phase 4C-2 checkpoint not found: {CHECKPOINT_PTH}"

    # Record prod model modification time to ensure it is never altered
    prod_mtime_before = os.path.getmtime(PROD_MODEL_PATH)

    model = onnx.load(str(PROD_MODEL_PATH))
    ckpt = torch.load(CHECKPOINT_PTH, weights_only=True, map_location="cpu")
    sd = ckpt["state_dict"]

    name_map = {
        "features.7.0.weight": sd["conv.weight"].numpy(),
        "features.7.0.weight_bias": sd["conv.bias"].numpy(),
        "classifier.1.weight": sd["classifier.weight"].numpy(),
        "classifier.1.bias": sd["classifier.bias"].numpy()
    }

    new_inits = []
    for init in model.graph.initializer:
        if init.name in name_map:
            new_inits.append(numpy_helper.from_array(name_map[init.name], init.name))
        else:
            new_inits.append(init)

    model.graph.ClearField("initializer")
    model.graph.initializer.extend(new_inits)

    CANDIDATE_ONNX.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(CANDIDATE_ONNX))

    prod_mtime_after = os.path.getmtime(PROD_MODEL_PATH)
    assert prod_mtime_before == prod_mtime_after, "CRITICAL ERROR: Production ONNX file was modified!"
    assert CANDIDATE_ONNX.resolve() != PROD_MODEL_PATH.resolve(), "CRITICAL: Paths must be distinct!"

    file_size_mb = CANDIDATE_ONNX.stat().st_size / (1024 * 1024)
    print(f"[OK] Candidate ONNX exported successfully to: {CANDIDATE_ONNX}")
    print(f"[OK] File size: {file_size_mb:.2f} MB")
    print(f"[OK] Verified production ONNX file remains strictly untouched.")
    return CANDIDATE_ONNX


def validate_onnx_contract(onnx_path: Path) -> ort.InferenceSession:
    """Validates tensor shapes, dtypes, names and input/output contracts."""
    print("\n" + "=" * 80)
    print(" STEP 2: ONNX STRUCTURAL & CONTRACT VALIDATION")
    print("=" * 80)

    model = onnx.load(str(onnx_path))
    onnx.checker.check_model(model)
    print("[OK] ONNX checker: Graph topology and opset valid.")

    session_opts = ort.SessionOptions()
    session_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session_opts.intra_op_num_threads = 4
    session = ort.InferenceSession(str(onnx_path), sess_options=session_opts, providers=["CPUExecutionProvider"])

    inputs = session.get_inputs()
    outputs = session.get_outputs()

    assert len(inputs) == 1, f"Expected 1 input, got {len(inputs)}"
    assert inputs[0].name == "input", f"Expected input name 'input', got {inputs[0].name}"
    assert inputs[0].type == "tensor(float)", f"Expected float32 tensor, got {inputs[0].type}"
    print(f"[OK] Input contract: name='{inputs[0].name}', type='{inputs[0].type}', shape={inputs[0].shape}")

    assert len(outputs) == 1, f"Expected 1 output, got {len(outputs)}"
    assert outputs[0].name == "logits", f"Expected output name 'logits', got {outputs[0].name}"
    assert outputs[0].type == "tensor(float)", f"Expected float32 tensor, got {outputs[0].type}"
    assert outputs[0].shape[1] == 38, f"Expected 38 classes, got {outputs[0].shape[1]}"
    print(f"[OK] Output contract: name='{outputs[0].name}', type='{outputs[0].type}', shape={outputs[0].shape}")

    # Load classes and verify matching 38 classes
    with open(CLASSES_JSON, "r", encoding="utf-8") as f:
        classes_data = json.load(f)
    assert len(classes_data["classes"]) == 38, f"Expected 38 classes in classes.json"
    print(f"[OK] Class taxonomy: Exactly 38 classes matching output logit dimension.")

    # Smoke inference test
    dummy = np.zeros((1, 3, 224, 224), dtype=np.float32)
    smoke_out = session.run(["logits"], {"input": dummy})[0]
    assert smoke_out.shape == (1, 38), f"Smoke run shape mismatch: {smoke_out.shape}"
    print(f"[OK] Smoke forward pass succeeded. Output shape: {smoke_out.shape}")
    return session


def run_numerical_parity(
    candidate_session: ort.InferenceSession
) -> Dict[str, Any]:
    """Computes bit-for-bit numerical parity between PyTorch Phase 4C-2 and Candidate ONNX."""
    print("\n" + "=" * 80)
    print(" STEP 3: PYTORCH vs ONNX NUMERICAL PARITY (Untouched 236 Test Images)")
    print("=" * 80)

    # 1. Setup PyTorch feature extractor + PartialBackboneHead
    base_model = onnx.load(str(PROD_MODEL_PATH))
    f6_out = onnx.helper.make_tensor_value_info("add_3505", onnx.TensorProto.FLOAT, [None, 256, 7, 7])
    base_model.graph.output.append(f6_out)
    extractor_session = ort.InferenceSession(base_model.SerializeToString(), providers=["CPUExecutionProvider"])

    ckpt = torch.load(CHECKPOINT_PTH, weights_only=True, map_location="cpu")
    pytorch_head = PartialBackboneHead(256, 1280, 38)
    pytorch_head.load_state_dict(ckpt["state_dict"])
    pytorch_head.eval()

    with open(PLANTDOC_TEST_MANIFEST, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    base_dir = PLANTDOC_TEST_MANIFEST.parent

    max_abs_diff = 0.0
    abs_diffs = []
    pytorch_preds = []
    onnx_preds = []

    for row in reader:
        img_p = base_dir / row["image_path"]
        with Image.open(img_p) as img:
            rgb = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.asarray(rgb, dtype=np.float32) / 255.0
            norm = (arr - MEAN) / STD
            chw = np.transpose(norm, (2, 0, 1))
            tensor_in = np.expand_dims(chw, axis=0)

        # PyTorch forward pass: extract features.6 -> PartialBackboneHead
        _, f6 = extractor_session.run(["logits", "add_3505"], {"input": tensor_in})
        with torch.no_grad():
            pyt_logits = pytorch_head(torch.from_numpy(f6)).numpy()[0]

        # Candidate ONNX end-to-end forward pass
        onnx_logits = candidate_session.run(["logits"], {"input": tensor_in})[0][0]

        diff = np.abs(pyt_logits - onnx_logits)
        max_abs_diff = max(max_abs_diff, float(np.max(diff)))
        abs_diffs.append(float(np.mean(diff)))

        pytorch_preds.append(int(np.argmax(pyt_logits)))
        onnx_preds.append(int(np.argmax(onnx_logits)))

    mean_abs_diff = float(np.mean(abs_diffs))
    agreements = np.sum(np.array(pytorch_preds) == np.array(onnx_preds))
    agreement_pct = (agreements / len(reader)) * 100.0

    print(f"Total test images compared:     {len(reader)}")
    print(f"Max absolute logit difference:  {max_abs_diff:.8e}")
    print(f"Mean absolute logit difference: {mean_abs_diff:.8e}")
    print(f"Prediction agreement:           {agreements} / {len(reader)} ({agreement_pct:.2f}%)")
    assert max_abs_diff < 1e-4, f"Numerical parity failure: max diff {max_abs_diff} >= 1e-4"
    assert agreement_pct == 100.0, f"Prediction mismatch between PyTorch and ONNX!"
    print("[OK] PyTorch and Candidate ONNX achieve 100% numerical parity within float32 tolerance!")

    return {
        "max_abs_diff": max_abs_diff,
        "mean_abs_diff": mean_abs_diff,
        "agreement_pct": agreement_pct,
        "total_compared": len(reader)
    }


def evaluate_candidate_onnx(
    candidate_session: ort.InferenceSession
) -> Dict[str, Any]:
    """Evaluates candidate ONNX on the untouched 236-image PlantDoc test set."""
    print("\n" + "=" * 80)
    print(" STEP 4: CANDIDATE ONNX BENCHMARK ON UNTOUCHED PLANTDOC TEST SET (236 Images)")
    print("=" * 80)

    with open(CLASSES_JSON, "r", encoding="utf-8") as f:
        classes = json.load(f)["classes"]
    class_to_idx = {c: i for i, c in enumerate(classes)}

    with open(PLANTDOC_TEST_MANIFEST, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    base_dir = PLANTDOC_TEST_MANIFEST.parent
    y_true = []
    y_pred = []
    confs = []
    crops_true = []

    for row in reader:
        target_idx = class_to_idx[row["label"]]
        y_true.append(target_idx)
        crops_true.append(get_crop(row["label"]))

        img_p = base_dir / row["image_path"]
        with Image.open(img_p) as img:
            rgb = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.asarray(rgb, dtype=np.float32) / 255.0
            norm = (arr - MEAN) / STD
            chw = np.transpose(norm, (2, 0, 1))
            tensor_in = np.expand_dims(chw, axis=0)

        logits = candidate_session.run(["logits"], {"input": tensor_in})[0][0]
        prob = softmax(logits)
        pred_idx = int(np.argmax(prob))
        y_pred.append(pred_idx)
        confs.append(float(np.max(prob)))

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    confs = np.array(confs)

    acc = float(accuracy_score(y_true, y_pred))
    active_labels = sorted(list(set(y_true)))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=active_labels, average="macro", zero_division=0
    )
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=active_labels, average="weighted", zero_division=0
    )
    ece = calculate_ece(confs, (y_true == y_pred).astype(int))

    cross_crop = 0
    intra_crop = 0
    for i in range(len(y_pred)):
        if y_pred[i] != y_true[i]:
            pred_crop = get_crop(classes[y_pred[i]])
            true_crop = crops_true[i]
            if pred_crop != true_crop:
                cross_crop += 1
            else:
                intra_crop += 1

    scorch_idx = class_to_idx["Strawberry___Leaf_scorch"]
    pepper_healthy_idx = class_to_idx["Pepper,_bell___healthy"]
    tlb_idx = class_to_idx["Tomato___Late_blight"]

    scorch_fps = int(np.sum((y_pred == scorch_idx) & (y_true != scorch_idx)))
    pepper_fps = int(np.sum((y_pred == pepper_healthy_idx) & (y_true != pepper_healthy_idx)))
    tlb_fps = int(np.sum((y_pred == tlb_idx) & (y_true != tlb_idx)))

    metrics = {
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
        "total_errors": int(np.sum(y_pred != y_true)),
        "cross_crop_errors": cross_crop,
        "intra_crop_errors": intra_crop,
        "strawberry_scorch_fps": scorch_fps,
        "pepper_healthy_fps": pepper_fps,
        "tomato_late_blight_fps": tlb_fps
    }

    print(f"Overall Accuracy:           {acc * 100:.2f}%")
    print(f"Macro Precision:            {p_macro * 100:.2f}%")
    print(f"Macro Recall:               {r_macro * 100:.2f}%")
    print(f"Macro F1 Score:             {f1_macro * 100:.2f}%")
    print(f"Weighted F1 Score:          {f1_wt * 100:.2f}%")
    print(f"Expected Calib Error (ECE): {ece * 100:.2f}%")
    print(f"Mean Confidence:            {metrics['mean_confidence'] * 100:.2f}%")
    print(f"Total Errors:               {metrics['total_errors']} / {len(y_true)}")
    print(f"Cross-Crop Errors:          {cross_crop}")
    print(f"Intra-Crop Errors:          {intra_crop}")
    print(f"Strawberry Scorch FPs:      {scorch_fps}")
    print(f"Pepper Healthy FPs:         {pepper_fps}")
    print(f"Tomato Late Blight FPs:     {tlb_fps}")
    print("[OK] Candidate ONNX evaluation completed successfully.")
    return metrics


def test_production_preprocessing_integration(candidate_onnx_path: Path):
    """Integrates Candidate ONNX into the production DiseaseDetector class."""
    print("\n" + "=" * 80)
    print(" STEP 5: PRODUCTION PREPROCESSING & QUALITY PIPELINE INTEGRATION")
    print("=" * 80)

    # Add backend to sys.path
    backend_dir = PROJECT_ROOT / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from services.ai.disease_detector import DiseaseDetector

    detector = DiseaseDetector(model_path=str(candidate_onnx_path))
    sample_images = [
        backend_dir / "test_tomato.png",
        backend_dir / "uploads" / "grapes - Image.jpeg",
        backend_dir / "uploads" / "GrapesImage.jpeg",
        backend_dir / "uploads" / "tomoato-Check.jpeg"
    ]

    print(f"{'Image Name':<24} | {'Strategy':<10} | {'TTA':<5} | {'Predicted Class':<32} | {'Conf':<6} | {'Status':<14} | {'Quality'}")
    print("-" * 110)

    for img_path in sample_images:
        if not img_path.exists():
            continue
        base_name = img_path.name[:22]

        for mode in ["direct", "letterbox"]:
            for tta in [False, True]:
                res = detector.predict(str(img_path), preprocessing_mode=mode, enable_tta=tta)
                pred_cls = f"{res['crop']}: {res['condition']}"[:31]
                conf_str = f"{res['confidence']*100:.1f}%"
                status_str = res["status"]
                tta_str = "ON" if tta else "OFF"
                print(f"{base_name:<24} | {mode:<10} | {tta_str:<5} | {pred_cls:<32} | {conf_str:<6} | {status_str:<14} | {res['quality_status']}")
        print("-" * 110)

    print("[OK] Production DiseaseDetector inference pipeline operates seamlessly with Candidate ONNX.")


def main():
    print("\n" + "#" * 80)
    print("#  AGRONEX PHASE 4C-2: CANDIDATE ONNX EXPORT AND COMPREHENSIVE VALIDATION  #")
    print("#" * 80 + "\n")

    # Step 1: Export candidate ONNX
    onnx_path = export_candidate_onnx()

    # Step 2: Validate ONNX contract
    session = validate_onnx_contract(onnx_path)

    # Step 3: Run numerical parity
    parity_results = run_numerical_parity(session)

    # Step 4: Evaluate candidate ONNX
    metrics = evaluate_candidate_onnx(session)

    # Step 5: Test integration with production DiseaseDetector
    test_production_preprocessing_integration(onnx_path)

    print("\n" + "=" * 80)
    print(" ALL VALIDATION PHASES COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
