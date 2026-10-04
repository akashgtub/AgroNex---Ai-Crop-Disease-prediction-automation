"""
AgroNex Phase 4C-2: Partial Backbone Fine-Tuning + Domain Replay
Unfreezes features.7 (lr=1e-5) and classifier.1 (lr=1e-4), keeping earlier layers frozen.
Trains on a domain-replay mixture:
  - 540 PlantDoc field images (augmented 4x = 2160 views)
  - 190 PlantVillage studio images (anchor studio views, unaugmented)
Tracks validation on PlantDoc val split and saves best checkpoint.
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
PLANTDOC_TRAIN_MANIFEST = Path(__file__).resolve().parent / "manifests" / "plantdoc_train_manifest.csv"
PLANTDOC_VAL_MANIFEST = Path(__file__).resolve().parent / "manifests" / "plantdoc_val_manifest.csv"
PLANTVILLAGE_REPLAY_MANIFEST = PROJECT_ROOT / "backend" / "evaluation" / "manifests" / "plantvillage_sanity_manifest.csv"
CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


def image_to_tensor(img: Image.Image) -> np.ndarray:
    resized = img.resize((224, 224), Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    norm = (arr - MEAN) / STD
    chw = np.transpose(norm, (2, 0, 1))
    return np.expand_dims(chw, axis=0)


def generate_plantdoc_augmentations(img: Image.Image) -> List[Image.Image]:
    """Generates 3 field-oriented augmentations of a single training image."""
    views = [img]  # View 1: Original
    views.append(img.transpose(Image.FLIP_LEFT_RIGHT))  # View 2: Horizontal flip
    enh_b = ImageEnhance.Brightness(img).enhance(random.uniform(0.85, 1.15))
    enh_c = ImageEnhance.Contrast(enh_b).enhance(random.uniform(0.85, 1.15))
    views.append(enh_c)  # View 3: Glare/Contrast adjustment
    angle = random.uniform(-12, 12)
    rotated = img.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=(128, 128, 128))
    views.append(rotated)  # View 4: Slight rotation
    return views


def setup_feature_extractor() -> Tuple[ort.InferenceSession, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Loads production ONNX model and adds 'add_3505' (output of features.6, shape [None, 256, 7, 7])
    to the outputs so features.0..6 can serve as a bit-for-bit frozen feature extractor.
    """
    model = onnx.load(str(MODEL_PATH))
    f6_out = onnx.helper.make_tensor_value_info("add_3505", onnx.TensorProto.FLOAT, [None, 256, 7, 7])
    model.graph.output.append(f6_out)

    session_opts = ort.SessionOptions()
    session_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session_opts.intra_op_num_threads = 4
    session = ort.InferenceSession(model.SerializeToString(), sess_options=session_opts, providers=["CPUExecutionProvider"])

    init_map = {init.name: numpy_helper.to_array(init) for init in model.graph.initializer}
    w_f7 = init_map["features.7.0.weight"].copy()        # (1280, 256, 1, 1)
    b_f7 = init_map["features.7.0.weight_bias"].copy()   # (1280,)
    w_cls = init_map["classifier.1.weight"].copy()       # (38, 1280)
    b_cls = init_map["classifier.1.bias"].copy()         # (38,)

    return session, w_f7, b_f7, w_cls, b_cls


class PartialBackboneHead(nn.Module):
    """
    Trainable stage:
      - features.7: Conv2d(256, 1280, 1x1) + SiLU + AdaptiveAvgPool2d(1)
      - classifier.1: Linear(1280, 38)
    Initialized with the exact production ONNX weights.
    """

    def __init__(self, w_f7: np.ndarray, b_f7: np.ndarray, w_cls: np.ndarray, b_cls: np.ndarray):
        super().__init__()
        self.conv = nn.Conv2d(256, 1280, kernel_size=1, bias=True)
        with torch.no_grad():
            self.conv.weight.copy_(torch.from_numpy(w_f7))
            self.conv.bias.copy_(torch.from_numpy(b_f7))

        self.act = nn.SiLU()
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(0.2)
        self.classifier = nn.Linear(1280, 38, bias=True)
        with torch.no_grad():
            self.classifier.weight.copy_(torch.from_numpy(w_cls))
            self.classifier.bias.copy_(torch.from_numpy(b_cls))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.act(self.conv(x))
        pooled = torch.flatten(self.pool(h), 1)
        dropped = self.dropout(pooled)
        return self.classifier(dropped)


def extract_features(
    manifest_path: Path,
    session: ort.InferenceSession,
    augment: bool = False
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Extracts (N, 256, 7, 7) frozen spatial feature maps from a manifest."""
    base_dir = manifest_path.parent
    features = []
    labels = []

    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print(f"[INFO] Extracting features for {len(reader)} images from {manifest_path.name} (augment={augment})...")
    start = time.time()

    for row in reader:
        img_path = base_dir / row["image_path"]
        target_idx = int(row["agro_index"])

        with Image.open(img_path) as raw_img:
            img_rgb = raw_img.convert("RGB")
            views = generate_plantdoc_augmentations(img_rgb) if augment else [img_rgb]

            for view in views:
                tensor_input = image_to_tensor(view)
                _, f6_view = session.run(["logits", "add_3505"], {"input": tensor_input})
                features.append(f6_view[0])
                labels.append(target_idx)

    elapsed = time.time() - start
    print(f"[INFO] Extracted {len(features)} feature maps in {elapsed:.2f}s.")
    return torch.tensor(np.array(features), dtype=torch.float32), torch.tensor(labels, dtype=torch.long)


def train_phase4c2(
    epochs: int = 25,
    lr_backbone: float = 1e-5,
    lr_head: float = 1e-4,
    weight_decay: float = 1e-4,
    batch_size: int = 32,
    seed: int = 42
) -> Tuple[Path, Dict]:
    set_seed(seed)
    print("\n" + "=" * 80)
    print(" AGRONEX PHASE 4C-2: PARTIAL BACKBONE FINE-TUNING + DOMAIN REPLAY (features.7 + Head)")
    print("=" * 80)

    # 1. Setup session and initial weights
    session, w_f7, b_f7, w_cls, b_cls = setup_feature_extractor()

    # 2. Extract features for PlantDoc train (augmented 4x)
    X_pd_train, y_pd_train = extract_features(PLANTDOC_TRAIN_MANIFEST, session, augment=True)

    # 3. Extract features for PlantVillage replay (anchor studio, unaugmented 1x)
    X_pv_replay, y_pv_replay = extract_features(PLANTVILLAGE_REPLAY_MANIFEST, session, augment=False)

    # Combine PlantDoc + PlantVillage for domain replay training
    X_train = torch.cat([X_pd_train, X_pv_replay], dim=0)
    y_train = torch.cat([y_pd_train, y_pv_replay], dim=0)
    print(f"[DATASET] Domain-Replay Training Set: {len(X_train)} samples ({len(X_pd_train)} PlantDoc + {len(X_pv_replay)} PlantVillage replay)")

    # 4. Extract features for PlantDoc validation set
    X_val, y_val = extract_features(PLANTDOC_VAL_MANIFEST, session, augment=False)
    # Also extract features for PlantVillage validation check
    X_pv_val, y_pv_val = X_pv_replay, y_pv_replay

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)

    # 5. Initialize PartialBackboneHead with production weights
    model = PartialBackboneHead(w_f7, b_f7, w_cls, b_cls)
    criterion = nn.CrossEntropyLoss()

    # Differential learning rates: 1e-5 for features.7, 1e-4 for classifier.1
    optimizer = torch.optim.AdamW([
        {"params": model.conv.parameters(), "lr": lr_backbone, "weight_decay": weight_decay},
        {"params": model.classifier.parameters(), "lr": lr_head, "weight_decay": weight_decay}
    ])

    # Initial epoch 0 baseline check
    model.eval()
    with torch.no_grad():
        val_logits = model(X_val)
        val_preds = torch.argmax(val_logits, dim=-1)
        val_acc_init = float((val_preds == y_val).float().mean())
        val_loss_init = float(criterion(val_logits, y_val))

        pv_logits = model(X_pv_val)
        pv_preds = torch.argmax(pv_logits, dim=-1)
        pv_acc_init = float((pv_preds == y_pv_val).float().mean())

    print(f"\n[EPOCH 0 / Baseline Init] PlantDoc Val Acc: {val_acc_init * 100:.2f}% | PlantVillage Acc: {pv_acc_init * 100:.2f}%")

    best_val_acc = val_acc_init
    best_val_loss = val_loss_init
    best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
    best_epoch = 0

    history = []

    print("-" * 80)
    print(f"{'Epoch':<6} | {'Train Loss':<11} | {'Val Loss':<10} | {'PD Val Acc':<11} | {'PV Replay Acc':<14} | {'Status'}")
    print("-" * 80)

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

            pv_logits = model(X_pv_val)
            pv_preds = torch.argmax(pv_logits, dim=-1)
            pv_acc = float((pv_preds == y_pv_val).float().mean())

        improved = False
        if val_acc > best_val_acc or (val_acc == best_val_acc and val_loss < best_val_loss):
            best_val_acc = val_acc
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            improved = True

        status = f"BEST (Epoch {best_epoch})" if improved else ""
        print(f"{epoch:<6} | {train_loss:<11.4f} | {val_loss:<10.4f} | {val_acc * 100:6.2f}%    | {pv_acc * 100:6.2f}%        | {status}")

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "pv_acc": pv_acc
        })

    # Save checkpoint
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / "phase4c2_best_model.pth"
    torch.save({
        "state_dict": best_weights,
        "best_epoch": best_epoch,
        "best_val_acc": best_val_acc,
        "config": {
            "epochs": epochs,
            "lr_backbone": lr_backbone,
            "lr_head": lr_head,
            "weight_decay": weight_decay,
            "batch_size": batch_size,
            "seed": seed
        },
        "history": history
    }, ckpt_path)

    print("-" * 80)
    print(f"[INFO] Best Phase 4C-2 checkpoint saved to: {ckpt_path}")
    print(f"[INFO] Best PlantDoc Val Accuracy: {best_val_acc * 100:.2f}% (Epoch {best_epoch})\n")

    return ckpt_path, {
        "best_epoch": best_epoch,
        "best_val_acc": best_val_acc,
        "history": history
    }


if __name__ == "__main__":
    train_phase4c2()
