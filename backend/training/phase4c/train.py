"""
AgroNex Phase 4C: Controlled Fine-Tuning Script
Fine-tunes the classification head initialized with production ONNX weights,
freezing the EfficientNetV2-S backbone, using field-augmented PlantDoc training data.
"""

import csv
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import onnx
from onnx import numpy_helper
import onnxruntime as ort
from PIL import Image, ImageEnhance
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "efficientnet_v2_s_best.onnx"
CLASSES_JSON = PROJECT_ROOT / "backend" / "models" / "classes.json"
TRAIN_MANIFEST = Path(__file__).resolve().parent / "manifests" / "plantdoc_train_manifest.csv"
VAL_MANIFEST = Path(__file__).resolve().parent / "manifests" / "plantdoc_val_manifest.csv"
CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# Setup feature extractor using ONNX model intermediate output 'view' (1280-dim)
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


# Normalization constants (ImageNet)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


def image_to_tensor(img: Image.Image) -> np.ndarray:
    resized = img.resize((224, 224), Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    norm = (arr - MEAN) / STD
    chw = np.transpose(norm, (2, 0, 1))
    return np.expand_dims(chw, axis=0)


def generate_augmented_views(img: Image.Image) -> List[Image.Image]:
    """Generates 3 field-oriented augmentations of a single training image."""
    views = [img]  # View 1: Original

    # View 2: Horizontal flip
    views.append(img.transpose(Image.FLIP_LEFT_RIGHT))

    # View 3: Color jitter (brightness & contrast adjustment to simulate sun glare / shade)
    enh_b = ImageEnhance.Brightness(img).enhance(random.uniform(0.85, 1.15))
    enh_c = ImageEnhance.Contrast(enh_b).enhance(random.uniform(0.85, 1.15))
    views.append(enh_c)

    # View 4: Slight rotation (+/- 12 deg)
    angle = random.uniform(-12, 12)
    rotated = img.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=(128, 128, 128))
    views.append(rotated)

    return views


def extract_features_from_manifest(
    manifest_path: Path,
    session: ort.InferenceSession,
    augment: bool = False
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Extracts 1280-dim frozen features and ground-truth labels from a manifest."""
    base_dir = manifest_path.parent
    features = []
    labels = []

    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print(f"[INFO] Extracting features for {len(reader)} images from {manifest_path.name} (augment={augment})...")
    start_time = time.time()

    for row in reader:
        img_path = base_dir / row["image_path"]
        target_idx = int(row["agro_index"])

        with Image.open(img_path) as raw_img:
            img_rgb = raw_img.convert("RGB")
            views = generate_augmented_views(img_rgb) if augment else [img_rgb]

            for view in views:
                tensor_input = image_to_tensor(view)
                _, feat_view = session.run(["logits", "view"], {"input": tensor_input})
                features.append(feat_view[0])
                labels.append(target_idx)

    elapsed = time.time() - start_time
    print(f"[INFO] Extracted {len(features)} feature vectors in {elapsed:.2f}s.")
    return torch.tensor(np.array(features), dtype=torch.float32), torch.tensor(labels, dtype=torch.long)


class LinearClassifierHead(nn.Module):
    """Classification head initialized with production ONNX weights."""

    def __init__(self, in_features: int = 1280, num_classes: int = 38, w_init=None, b_init=None):
        super().__init__()
        self.linear = nn.Linear(in_features, num_classes)
        if w_init is not None and b_init is not None:
            with torch.no_grad():
                self.linear.weight.copy_(torch.from_numpy(w_init))
                self.linear.bias.copy_(torch.from_numpy(b_init))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


def train_head(
    epochs: int = 25,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
    batch_size: int = 32,
    seed: int = 42
) -> Tuple[Path, Dict[str, Any]]:
    set_seed(seed)
    print("\n" + "=" * 70)
    print("      AGRONEX PHASE 4C-1: DOMAIN ADAPTATION CONTROLLED FINE-TUNING     ")
    print("=" * 70)

    # 1. Setup session and initial weights
    session, w_init, b_init = setup_feature_extractor()

    # 2. Extract features
    X_train, y_train = extract_features_from_manifest(TRAIN_MANIFEST, session, augment=True)
    X_val, y_val = extract_features_from_manifest(VAL_MANIFEST, session, augment=False)

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)

    # 3. Initialize Head
    model = LinearClassifierHead(1280, 38, w_init, b_init)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # Initial validation before training (epoch 0 baseline check)
    model.eval()
    with torch.no_grad():
        val_logits = model(X_val)
        val_preds = torch.argmax(val_logits, dim=-1)
        val_acc_init = float((val_preds == y_val).float().mean())
        val_loss_init = float(criterion(val_logits, y_val))
    print(f"\n[EPOCH 0 / Baseline Init] Val Loss: {val_loss_init:.4f} | Val Accuracy: {val_acc_init * 100:.2f}%")

    best_val_acc = val_acc_init
    best_val_loss = val_loss_init
    best_weights = model.state_dict()
    best_epoch = 0

    history = []

    print("-" * 70)
    print(f"{'Epoch':<8} | {'Train Loss':<12} | {'Val Loss':<12} | {'Val Accuracy':<14} | {'Status'}")
    print("-" * 70)

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss_total = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            train_loss_total += loss.item() * len(batch_y)

        train_loss = train_loss_total / len(X_train)

        model.eval()
        with torch.no_grad():
            val_logits = model(X_val)
            val_loss = float(criterion(val_logits, y_val))
            val_preds = torch.argmax(val_logits, dim=-1)
            val_acc = float((val_preds == y_val).float().mean())

        improved = False
        if val_acc > best_val_acc or (val_acc == best_val_acc and val_loss < best_val_loss):
            best_val_acc = val_acc
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            improved = True

        status = f"BEST (Epoch {best_epoch})" if improved else ""
        print(f"{epoch:<8} | {train_loss:<12.4f} | {val_loss:<12.4f} | {val_acc * 100:6.2f}%        | {status}")

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_acc": val_acc
        })

    # Save checkpoint
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / "phase4c_finetuned_head.pth"
    torch.save({
        "state_dict": best_weights,
        "best_epoch": best_epoch,
        "best_val_acc": best_val_acc,
        "config": {
            "epochs": epochs,
            "lr": lr,
            "weight_decay": weight_decay,
            "batch_size": batch_size,
            "seed": seed
        },
        "history": history
    }, ckpt_path)

    print("-" * 70)
    print(f"[INFO] Best model checkpoint saved to: {ckpt_path}")
    print(f"[INFO] Best Val Accuracy: {best_val_acc * 100:.2f}% (Epoch {best_epoch})\n")

    return ckpt_path, {
        "best_epoch": best_epoch,
        "best_val_acc": best_val_acc,
        "history": history
    }


if __name__ == "__main__":
    train_head()
