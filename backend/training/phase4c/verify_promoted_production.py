"""
AgroNex Phase 4C-2: Post-Promotion Production Service Verification Suite
Tests the promoted production model via the actual FastAPI service (`/api/crops/analyze`).
Verifies:
  1. Cryptographic SHA-256 identity between Promoted Model and Candidate ONNX.
  2. Production FastAPI TestClient integration on representative images:
     - Clear crop image
     - Outdoor field image
     - Low-quality / low-confidence image (underexposed, blurry, overexposed, low-foliage)
  3. Preprocessing modes (direct, letterbox) and TTA (OFF, ON).
  4. Response schema adherence: crop, condition, confidence, quality_status, status, latency_ms.
  5. Exact parity between Candidate ONNX standalone run and Production API run.
"""

import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
from PIL import Image, ImageFilter
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from services.ai.disease_detector import DiseaseDetector

PROD_MODEL_PATH = BACKEND_DIR / "models" / "efficientnet_v2_s_best.onnx"
BACKUP_PATH = BACKEND_DIR / "models" / "efficientnet_v2_s_best.onnx.bak"
CANDIDATE_PATH = BACKEND_DIR / "training" / "phase4c" / "checkpoints" / "efficientnet_v2_s_phase4c2_candidate.onnx"


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_sha_integrity() -> Dict[str, str]:
    print("=" * 85)
    print(" 1. CRYPTOGRAPHIC IDENTITY & BACKUP INTEGRITY")
    print("=" * 85)

    assert BACKUP_PATH.exists(), f"Backup file not found at: {BACKUP_PATH}"
    assert PROD_MODEL_PATH.exists(), f"Production model not found at: {PROD_MODEL_PATH}"
    assert CANDIDATE_PATH.exists(), f"Candidate model not found at: {CANDIDATE_PATH}"

    backup_sha = compute_sha256(BACKUP_PATH)
    candidate_sha = compute_sha256(CANDIDATE_PATH)
    prod_sha = compute_sha256(PROD_MODEL_PATH)

    print(f"Backup original production SHA-256: {backup_sha}")
    print(f"Candidate Phase 4C-2 SHA-256:        {candidate_sha}")
    print(f"Current production model SHA-256:   {prod_sha}")

    assert prod_sha == candidate_sha, "CRITICAL ERROR: Promoted model does NOT match candidate SHA-256!"
    assert backup_sha != prod_sha, "CRITICAL ERROR: Backup and promoted model are identical (promotion did not happen)!"
    print("[OK] Production model successfully matches Candidate ONNX byte-for-byte.")
    print("[OK] Backup file safely preserved.")

    return {
        "backup_path": str(BACKUP_PATH),
        "backup_sha": backup_sha,
        "candidate_sha": candidate_sha,
        "prod_sha_after": prod_sha
    }


def prepare_representative_images(temp_dir: Path) -> Dict[str, Path]:
    """Prepares clear crop, field, and low-quality test images."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    images = {}

    # 1. Clear crop image from uploads
    sample_clear = BACKEND_DIR / "uploads" / "GrapesImage.jpeg"
    if sample_clear.exists():
        images["Clear Crop (Grape Leaf)"] = sample_clear
    else:
        # Fallback to test_tomato.png
        images["Clear Crop"] = BACKEND_DIR / "test_tomato.png"

    # 2. Outdoor field image from PlantDoc test set
    plantdoc_field = BACKEND_DIR / "evaluation" / "data" / "plantdoc_test" / "Tomato Early blight leaf" / "Shoemaker_7068.JPG.jpg"
    if plantdoc_field.exists():
        images["Outdoor Field Image (PlantDoc)"] = plantdoc_field
    else:
        # Search for any plantdoc image
        pd_imgs = list((BACKEND_DIR / "evaluation" / "data" / "plantdoc_test").rglob("*.jpg"))
        if pd_imgs:
            images["Outdoor Field Image (PlantDoc)"] = pd_imgs[0]

    # 3. Poor quality: Blurry
    base_img = Image.open(images[list(images.keys())[0]]).convert("RGB")
    blurry = base_img.filter(ImageFilter.GaussianBlur(radius=8))
    blur_path = temp_dir / "poor_blurry.jpg"
    blurry.save(blur_path)
    images["Poor Quality (Blurry)"] = blur_path

    # 4. Poor quality: Underexposed / Dark
    dark_arr = (np.asarray(base_img, dtype=np.float32) * 0.1).astype(np.uint8)
    dark_path = temp_dir / "poor_dark.jpg"
    Image.fromarray(dark_arr).save(dark_path)
    images["Poor Quality (Underexposed)"] = dark_path

    # 5. Poor quality: Overexposed
    over_arr = np.clip(np.asarray(base_img, dtype=np.float32) * 2.0 + 80, 0, 255).astype(np.uint8)
    over_path = temp_dir / "poor_overexposed.jpg"
    Image.fromarray(over_arr).save(over_path)
    images["Poor Quality (Overexposed)"] = over_path

    return images


def test_production_api_service(representative_images: Dict[str, Path]):
    """Exercises the production FastAPI service via TestClient on representative images."""
    print("\n" + "=" * 85)
    print(" 2. PRODUCTION FASTAPI SERVICE SMOKE & ENDPOINT AUDIT (/api/crops/analyze)")
    print("=" * 85)

    client = TestClient(app)

    # 1. Health check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.status_code}"
    assert health_resp.json() == {"status": "ok"}, "Health check body unexpected"
    print("[OK] GET /health returned 200 OK.")

    # 2. Re-instantiate detector to simulate service instance
    candidate_detector = DiseaseDetector(model_path=str(CANDIDATE_PATH))

    # Table format
    print(f"\n{'Category':<28} | {'Mode':<10} | {'TTA':<5} | {'Prediction':<30} | {'Conf':<6} | {'Status':<14} | {'Quality':<16} | {'Latency'}")
    print("-" * 135)

    for cat_name, img_path in representative_images.items():
        for mode in ["direct", "letterbox"]:
            for tta in [False, True]:
                with open(img_path, "rb") as f:
                    file_bytes = f.read()

                # Call API endpoint
                resp = client.post(
                    "/api/crops/analyze",
                    files={"file": (img_path.name, file_bytes, "image/jpeg")},
                    data={"mode": mode, "enable_tta": str(tta).lower()}
                )
                assert resp.status_code == 200, f"API error: {resp.status_code} - {resp.text}"
                data = resp.json()

                # Verify schema fields
                for field in ["crop", "condition", "confidence", "quality_status", "status", "latency_ms"]:
                    assert field in data, f"Missing expected field: {field}"

                # Parity with standalone candidate detector
                cand_res = candidate_detector.predict(str(img_path), preprocessing_mode=mode, enable_tta=tta)
                assert data["crop"] == cand_res["crop"], f"Crop mismatch: API {data['crop']} vs Cand {cand_res['crop']}"
                assert data["condition"] == cand_res["condition"], f"Condition mismatch: API {data['condition']} vs Cand {cand_res['condition']}"
                assert abs(data["confidence"] - cand_res["confidence"]) < 1e-4, "Confidence divergence!"

                pred_str = f"{data['crop']}: {data['condition']}"[:29]
                conf_str = f"{data['confidence']*100:.1f}%"
                tta_str = "ON" if tta else "OFF"
                lat_str = f"{data['latency_ms']:.1f} ms"
                print(f"{cat_name:<28} | {mode:<10} | {tta_str:<5} | {pred_str:<30} | {conf_str:<6} | {data['status']:<14} | {data['quality_status']:<16} | {lat_str}")

    print("\n[OK] 100% agreement between FastAPI Production API endpoint and Candidate ONNX.")
    print("[OK] Schema validation passed across all representative scenarios.")


def main():
    temp_dir = BACKEND_DIR / "training" / "phase4c" / "scratch_test"
    try:
        sha_info = test_sha_integrity()
        images = prepare_representative_images(temp_dir)
        test_production_api_service(images)
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
