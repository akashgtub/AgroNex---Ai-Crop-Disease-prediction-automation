"""
AgroNex Phase 4C: Dataset Acquisition & Manifest Generation for Domain Adaptation
Acquires a dedicated training and validation split from PlantDoc train/ (separate from the untouched test split).
"""

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"
CLASSES_JSON = PROJECT_ROOT / "backend" / "models" / "classes.json"

# Load 38 classes
with open(CLASSES_JSON, "r", encoding="utf-8") as f:
    cls_metadata = json.load(f)
CLASSES = cls_metadata["classes"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASSES)}

# Approved PlantDoc 27-class mapping table
PLANTDOC_MAPPING: Dict[str, Tuple[str, int, str]] = {
    "Apple Scab Leaf": ("Apple___Apple_scab", 0, "EXACT"),
    "Apple leaf": ("Apple___healthy", 3, "SEMANTIC"),
    "Apple rust leaf": ("Apple___Cedar_apple_rust", 2, "SEMANTIC"),
    "Bell_pepper leaf spot": ("Pepper,_bell___Bacterial_spot", 18, "SEMANTIC"),
    "Bell_pepper leaf": ("Pepper,_bell___healthy", 19, "SEMANTIC"),
    "Blueberry leaf": ("Blueberry___healthy", 4, "SEMANTIC"),
    "Cherry leaf": ("Cherry_(including_sour)___healthy", 6, "SEMANTIC"),
    "Corn Gray leaf spot": ("Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", 7, "EXACT"),
    "Corn leaf blight": ("Corn_(maize)___Northern_Leaf_Blight", 9, "SEMANTIC"),
    "Corn rust leaf": ("Corn_(maize)___Common_rust_", 8, "SEMANTIC"),
    "Peach leaf": ("Peach___healthy", 17, "SEMANTIC"),
    "Potato leaf early blight": ("Potato___Early_blight", 20, "EXACT"),
    "Potato leaf late blight": ("Potato___Late_blight", 21, "EXACT"),
    "Raspberry leaf": ("Raspberry___healthy", 23, "SEMANTIC"),
    "Soyabean leaf": ("Soybean___healthy", 24, "SEMANTIC"),
    "Squash Powdery mildew leaf": ("Squash___Powdery_mildew", 25, "EXACT"),
    "Strawberry leaf": ("Strawberry___healthy", 27, "SEMANTIC"),
    "Tomato Early blight leaf": ("Tomato___Early_blight", 29, "EXACT"),
    "Tomato Septoria leaf spot": ("Tomato___Septoria_leaf_spot", 32, "EXACT"),
    "Tomato leaf bacterial spot": ("Tomato___Bacterial_spot", 28, "EXACT"),
    "Tomato leaf late blight": ("Tomato___Late_blight", 30, "EXACT"),
    "Tomato leaf mosaic virus": ("Tomato___Tomato_mosaic_virus", 36, "EXACT"),
    "Tomato leaf yellow virus": ("Tomato___Tomato_Yellow_Leaf_Curl_Virus", 35, "SEMANTIC"),
    "Tomato leaf": ("Tomato___healthy", 37, "SEMANTIC"),
    "Tomato mold leaf": ("Tomato___Leaf_Mold", 31, "EXACT"),
    "grape leaf black rot": ("Grape___Black_rot", 11, "EXACT"),
    "grape leaf": ("Grape___healthy", 14, "SEMANTIC"),
}


def sanitize_filename(name: str) -> str:
    """Sanitizes filename for Windows filesystem compatibility."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def download_file(url: str, dest_path: Path, max_retries: int = 4, timeout: int = 25) -> bool:
    """Download single file with retries."""
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read()
                if len(content) == 0:
                    raise ValueError("Empty body")
                with open(dest_path, "wb") as f:
                    f.write(content)
            return True
        except Exception as e:
            if attempt == max_retries:
                print(f"[ERROR] Failed to download {url}: {e}")
                return False
            time.sleep(1.0 * attempt)
    return False


def acquire_training_data(
    train_samples_per_class: int = 20,
    val_samples_per_class: int = 5,
    seed: int = 42
) -> Tuple[Path, Path]:
    """
    Downloads and partitions PlantDoc train/ images into separate train and val splits.
    Returns (train_manifest_path, val_manifest_path).
    """
    print("\n--- [Phase 4C] Acquiring PlantDoc Training & Validation Sets ---")
    tree_url = "https://api.github.com/repos/pratikkayal/PlantDoc-Dataset/git/trees/master?recursive=1"
    req = urllib.request.Request(tree_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tree = json.loads(resp.read().decode())

    all_blobs = [x["path"] for x in tree.get("tree", []) if x["path"].startswith("train/") and x["type"] == "blob"]
    print(f"Total blobs discovered in PlantDoc train/: {len(all_blobs)}")

    # Group blobs by folder
    from collections import defaultdict
    folder_blobs = defaultdict(list)
    for p in all_blobs:
        parts = p.split("/")
        if len(parts) >= 3:
            folder = parts[1]
            folder_blobs[folder].append(p)

    import random
    rng = random.Random(seed)

    train_tasks = []
    val_tasks = []
    train_manifest_rows = []
    val_manifest_rows = []

    base_raw = "https://raw.githubusercontent.com/pratikkayal/PlantDoc-Dataset/master/"

    for pd_folder, (agro_cls, agro_idx, map_type) in PLANTDOC_MAPPING.items():
        if pd_folder not in folder_blobs:
            print(f"[WARN] Folder {pd_folder} not in train blobs!")
            continue

        blobs = sorted(folder_blobs[pd_folder])
        rng.shuffle(blobs)

        needed = train_samples_per_class + val_samples_per_class
        selected = blobs[:needed]

        train_subset = selected[:train_samples_per_class]
        val_subset = selected[train_samples_per_class:train_samples_per_class + val_samples_per_class]

        for p in train_subset:
            parts = p.split("/")
            fn = "/".join(parts[2:])
            safe_fn = sanitize_filename(fn)
            url = base_raw + urllib.parse.quote(p)
            dest = DATA_DIR / "train" / pd_folder / safe_fn
            train_tasks.append((url, dest))
            train_manifest_rows.append({
                "image_path": f"../data/train/{pd_folder}/{safe_fn}",
                "label": agro_cls,
                "agro_index": agro_idx,
                "mapping_type": map_type,
                "plantdoc_class": pd_folder,
                "split": "train"
            })

        for p in val_subset:
            parts = p.split("/")
            fn = "/".join(parts[2:])
            safe_fn = sanitize_filename(fn)
            url = base_raw + urllib.parse.quote(p)
            dest = DATA_DIR / "val" / pd_folder / safe_fn
            val_tasks.append((url, dest))
            val_manifest_rows.append({
                "image_path": f"../data/val/{pd_folder}/{safe_fn}",
                "label": agro_cls,
                "agro_index": agro_idx,
                "mapping_type": map_type,
                "plantdoc_class": pd_folder,
                "split": "val"
            })

    print(f"Selected {len(train_manifest_rows)} train images and {len(val_manifest_rows)} val images across 27 classes.")
    all_download_tasks = train_tasks + val_tasks
    print(f"Downloading/Verifying {len(all_download_tasks)} images concurrently...")

    success = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_file, url, dest): dest for url, dest in all_download_tasks}
        for future in as_completed(futures):
            dest = futures[future]
            if future.result():
                success += 1

    print(f"Download completed: {success}/{len(all_download_tasks)} images verified on disk.")

    # Write manifests
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    train_manifest_path = MANIFEST_DIR / "plantdoc_train_manifest.csv"
    with open(train_manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image_path", "label", "agro_index", "mapping_type", "plantdoc_class", "split"])
        writer.writeheader()
        writer.writerows(train_manifest_rows)

    val_manifest_path = MANIFEST_DIR / "plantdoc_val_manifest.csv"
    with open(val_manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image_path", "label", "agro_index", "mapping_type", "plantdoc_class", "split"])
        writer.writeheader()
        writer.writerows(val_manifest_rows)

    print(f"Saved train manifest: {train_manifest_path} ({len(train_manifest_rows)} rows)")
    print(f"Saved val manifest:   {val_manifest_path} ({len(val_manifest_rows)} rows)")

    # Integrity verification
    for manifest_p in [train_manifest_path, val_manifest_path]:
        with open(manifest_p, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                p = manifest_p.parent / row["image_path"]
                assert p.exists(), f"Missing file: {p}"
                with Image.open(p) as img:
                    img.verify()

    print("[PASS] 100% of train and val images verified readable with Pillow.")
    return train_manifest_path, val_manifest_path


if __name__ == "__main__":
    acquire_training_data()
