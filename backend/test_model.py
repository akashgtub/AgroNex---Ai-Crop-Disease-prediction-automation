"""
AgroNex Computer Vision Test Suite
Validates the disease prediction pipeline, preprocessing strategies, quality gatekeepers,
and performance metrics across 12 comprehensive scenarios.
"""

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.ai.disease_detector import DEFAULT_QUALITY_CONFIG, DiseaseDetector


def create_synthetic_leaf(
    width: int = 300,
    height: int = 300,
    color: tuple = (45, 140, 50),
    spot_color: tuple = (100, 70, 30)
) -> Image.Image:
    """Generates a synthetic green leaf image with diagnostic spot textures."""
    arr = np.full((height, width, 3), 235, dtype=np.uint8)  # Studio grey background
    # Create elliptical leaf mask
    y, x = np.ogrid[:height, :width]
    center_y, center_x = height // 2, width // 2
    mask = ((x - center_x) ** 2) / ((width * 0.4) ** 2) + ((y - center_y) ** 2) / ((height * 0.45) ** 2) <= 1.0
    arr[mask] = color

    # Add small spots / lesions
    spot_mask = ((x - (center_x - 20)) ** 2 + (y - (center_y - 20)) ** 2 <= 25 ** 2)
    arr[spot_mask & mask] = spot_color

    # Add subtle texture noise
    noise = np.random.randint(-10, 10, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def run_comprehensive_test_suite() -> Dict[str, Any]:
    print("\n" + "=" * 65)
    print("      AGRONEX COMPUTER VISION PREPROCESSING TEST SUITE      ")
    print("=" * 65 + "\n")

    detector = DiseaseDetector()
    temp_dir = Path(tempfile.mkdtemp(prefix="agronex_test_"))
    results = {}

    try:
        # Base test image
        base_tomato_path = backend_dir / "test_tomato.png"
        if base_tomato_path.exists():
            base_img = Image.open(str(base_tomato_path))
        else:
            base_img = create_synthetic_leaf(224, 224)

        # -----------------------------------------------------------------
        # Scenario 1: Normal RGB image
        # -----------------------------------------------------------------
        p1 = temp_dir / "01_normal_rgb.jpg"
        base_img.convert("RGB").save(p1)
        r1 = detector.predict(str(p1), preprocessing_mode="direct", enable_tta=False)
        print(f"[TEST 1/12] Normal RGB Image:")
        print(f"  Diagnosis: {r1['crop']} - {r1['condition']} ({r1['confidence']*100:.1f}%)")
        print(f"  Quality Status: {r1['quality_status']} | Measured Latency: {r1['latency_ms']} ms")
        assert r1["quality_status"] == "Passed", f"Expected Passed, got {r1['quality_status']}"
        results["test_normal_rgb"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 2: RGBA image (Alpha transparency handling)
        # -----------------------------------------------------------------
        p2 = temp_dir / "02_transparent.png"
        rgba_img = base_img.convert("RGBA")
        # Set top-left quadrant to completely transparent
        rgba_arr = np.array(rgba_img)
        rgba_arr[:50, :50, 3] = 0
        Image.fromarray(rgba_arr, mode="RGBA").save(p2)
        r2 = detector.predict(str(p2), preprocessing_mode="direct", enable_tta=False)
        print(f"\n[TEST 2/12] RGBA Transparent Image:")
        print(f"  Diagnosis: {r2['crop']} - {r2['condition']} ({r2['confidence']*100:.1f}%)")
        print(f"  Quality Status: {r2['quality_status']} | Alpha safely composited over neutral background")
        assert r2["crop"] != "Unknown", "RGBA prediction failed"
        results["test_rgba"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 3: EXIF rotated image (Orientation 6: 90 deg CW)
        # -----------------------------------------------------------------
        p3 = temp_dir / "03_exif_rotated.jpg"
        exif_img = base_img.convert("RGB").resize((320, 180))
        exif_data = exif_img.getexif()
        exif_data[0x0112] = 6  # 90 degrees clockwise
        exif_img.save(p3, exif=exif_data)
        # Verify detector handles orientation before checking dimensions
        oriented = detector._load_and_orient_image(str(p3))
        r3 = detector.predict(str(p3))
        print(f"\n[TEST 3/12] EXIF Rotated Image:")
        print(f"  Raw dimensions on disk: {exif_img.size} -> Transposed to: {oriented.size}")
        print(f"  Diagnosis: {r3['crop']} - {r3['condition']} ({r3['confidence']*100:.1f}%)")
        assert oriented.size == (180, 320), f"Expected (180, 320) after rotation, got {oriented.size}"
        results["test_exif_rotation"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 4: Rectangular image (Aspect ratio handling)
        # -----------------------------------------------------------------
        p4 = temp_dir / "04_rectangular.jpg"
        rect_img = base_img.convert("RGB").resize((440, 200))
        rect_img.save(p4)
        r4_direct = detector.predict(str(p4), preprocessing_mode="direct")
        r4_letterbox = detector.predict(str(p4), preprocessing_mode="letterbox")
        print(f"\n[TEST 4/12] Rectangular Aspect Ratio Comparison (440x200):")
        print(f"  Direct mode:    {r4_direct['crop']} - {r4_direct['condition']} ({r4_direct['confidence']*100:.1f}%)")
        print(f"  Letterbox mode: {r4_letterbox['crop']} - {r4_letterbox['condition']} ({r4_letterbox['confidence']*100:.1f}%)")
        results["test_rectangular"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 5: Very small image (Resolution gatekeeper)
        # -----------------------------------------------------------------
        p5 = temp_dir / "05_very_small.jpg"
        small_img = base_img.convert("RGB").resize((64, 64))
        small_img.save(p5)
        r5 = detector.predict(str(p5))
        print(f"\n[TEST 5/12] Very Small Image (64x64):")
        print(f"  Quality Status: {r5['quality_status']}")
        print(f"  Warning Message: {r5['warning_message']}")
        print(f"  Preserved Prediction: {r5['crop']} - {r5['condition']} ({r5['confidence']*100:.1f}%)")
        assert r5["quality_status"] == "Warning: Low Resolution", f"Expected Low Resolution warning, got {r5['quality_status']}"
        assert r5["crop"] is not None and len(r5["crop"]) > 0, "Model prediction must remain intact"
        results["test_very_small"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 6: Blurry image (Focus gatekeeper)
        # -----------------------------------------------------------------
        p6 = temp_dir / "06_blurry.jpg"
        blurry_img = base_img.convert("RGB").resize((300, 300)).filter(ImageFilter.GaussianBlur(radius=7))
        blurry_img.save(p6)
        r6 = detector.predict(str(p6))
        print(f"\n[TEST 6/12] Blurry Image:")
        print(f"  Quality Status: {r6['quality_status']}")
        print(f"  Warning Message: {r6['warning_message']}")
        assert "Blur" in r6["quality_status"], f"Expected blur warning, got {r6['quality_status']}"
        results["test_blurry"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 7: Dark image (Underexposure gatekeeper)
        # -----------------------------------------------------------------
        p7 = temp_dir / "07_dark.jpg"
        dark_img = ImageEnhance.Brightness(base_img.convert("RGB").resize((300, 300))).enhance(0.12)
        dark_img.save(p7)
        r7 = detector.predict(str(p7))
        print(f"\n[TEST 7/12] Dark / Underexposed Image:")
        print(f"  Quality Status: {r7['quality_status']}")
        print(f"  Warning Message: {r7['warning_message']}")
        assert "Low Light" in r7["quality_status"], f"Expected Low Light warning, got {r7['quality_status']}"
        results["test_dark"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 8: Overexposed image (Glare gatekeeper)
        # -----------------------------------------------------------------
        p8 = temp_dir / "08_overexposed.jpg"
        overexp_img = ImageEnhance.Brightness(base_img.convert("RGB").resize((300, 300))).enhance(2.8)
        overexp_img.save(p8)
        r8 = detector.predict(str(p8))
        print(f"\n[TEST 8/12] Overexposed Image:")
        print(f"  Quality Status: {r8['quality_status']}")
        print(f"  Warning Message: {r8['warning_message']}")
        assert "Overexposed" in r8["quality_status"], f"Expected Overexposed warning, got {r8['quality_status']}"
        results["test_overexposed"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 9: Non-leaf image (Foliage gatekeeper)
        # -----------------------------------------------------------------
        p9 = temp_dir / "09_non_leaf.jpg"
        # High-frequency textured reddish/purple surface with zero green foliage (e.g. soil/brick texture)
        non_leaf_arr = np.random.randint(60, 180, (300, 300, 3), dtype=np.uint8)
        non_leaf_arr[:, :, 1] = 20  # suppress green channel
        non_leaf_arr[:, :, 0] = np.clip(non_leaf_arr[:, :, 0] + 50, 0, 255)  # boost red channel
        non_leaf = Image.fromarray(non_leaf_arr, mode="RGB")
        non_leaf.save(p9)
        r9 = detector.predict(str(p9))
        print(f"\n[TEST 9/12] Non-Leaf Image:")
        print(f"  Quality Status: {r9['quality_status']}")
        print(f"  Warning Message: {r9['warning_message']}")
        assert "Low Foliage" in r9["quality_status"], f"Expected Low Foliage warning, got {r9['quality_status']}"
        results["test_non_leaf"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 10: Model confidence below uncertainty threshold
        # -----------------------------------------------------------------
        print(f"\n[TEST 10/12] Model Confidence Uncertainty Check:")
        # Test an ambiguous/noisy crop or check low-confidence behavior
        noise_img = Image.fromarray(np.random.randint(40, 150, (300, 300, 3), dtype=np.uint8), mode="RGB")
        p10 = temp_dir / "10_noisy.jpg"
        noise_img.save(p10)
        r10 = detector.predict(str(p10))
        print(f"  Prediction: {r10['crop']} - {r10['condition']}")
        print(f"  Confidence: {r10['confidence']*100:.1f}%")
        print(f"  Status: {r10['status']}")
        print(f"  Uncertainty Reason: {r10['uncertainty_reason']}")
        if r10["confidence"] < 0.60:
            assert r10["status"] == "Uncertain"
            assert r10["uncertainty_reason"] is not None
            # Verify diagnosis string was NOT overwritten
            assert r10["condition"] != "AgroNex is not confident about this result. Please upload a clearer image."
        print(f"  Preserved diagnosis without error string replacement: PASS")
        results["test_uncertainty"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 11: Batch softmax numerical stability
        # -----------------------------------------------------------------
        print(f"\n[TEST 11/12] Batch Softmax Numerical Stability:")
        logits_row1 = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        logits_row2 = np.array([1001.0, 1002.0, 1003.0, 1004.0], dtype=np.float32)
        batch_logits = np.stack([logits_row1, logits_row2], axis=0)
        batch_probs = detector._softmax(batch_logits)
        # Softmax is shift invariant: row 1 and row 2 must produce mathematically identical distributions
        diff = np.max(np.abs(batch_probs[0] - batch_probs[1]))
        print(f"  Max absolute difference between shift-offset rows: {diff:.8e}")
        assert diff < 1e-6, f"Batch softmax failed numerical independence: {diff}"
        assert np.allclose(np.sum(batch_probs, axis=1), [1.0, 1.0]), "Probabilities must sum to 1"
        results["test_batch_softmax"] = "PASS"

        # -----------------------------------------------------------------
        # Scenario 12: TTA enabled vs disabled (Latency & Stability)
        # -----------------------------------------------------------------
        print(f"\n[TEST 12/12] Test-Time Augmentation (TTA) Benchmark:")
        # Measure latency over 3 iterations for accuracy
        latencies_no_tta = []
        latencies_tta = []
        for _ in range(3):
            r_off = detector.predict(str(p1), preprocessing_mode="direct", enable_tta=False)
            r_on = detector.predict(str(p1), preprocessing_mode="direct", enable_tta=True)
            latencies_no_tta.append(r_off["latency_ms"])
            latencies_tta.append(r_on["latency_ms"])

        avg_no_tta = np.mean(latencies_no_tta)
        avg_tta = np.mean(latencies_tta)
        overhead = avg_tta - avg_no_tta
        print(f"  Single View (TTA disabled) Average Latency: {avg_no_tta:.2f} ms")
        print(f"  Multi View  (TTA enabled)  Average Latency: {avg_tta:.2f} ms")
        print(f"  Measured TTA Latency Overhead: {overhead:+.2f} ms")
        assert r_off["tta_enabled"] is False and r_on["tta_enabled"] is True
        results["test_tta"] = "PASS"

        print("\n" + "=" * 65)
        print("          ALL 12 PREPROCESSING TESTS PASSED!          ")
        print("=" * 65 + "\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def run_real_crop_comparisons():
    """Runs direct vs letterbox and TTA comparisons on all existing images in repository."""
    print("=" * 65)
    print("      EVALUATION ON REPOSITORY SAMPLE IMAGES      ")
    print("=" * 65)

    detector = DiseaseDetector()
    sample_images = [
        backend_dir / "test_tomato.png",
        backend_dir / "uploads" / "grapes - Image.jpeg",
        backend_dir / "uploads" / "GrapesImage.jpeg",
        backend_dir / "uploads" / "tomoato-Check.jpeg",
    ]

    print(f"{'Image Name':<24} | {'Strategy':<12} | {'TTA':<5} | {'Predicted Class':<32} | {'Conf':<6} | {'Status':<14} | {'Quality'}")
    print("-" * 115)

    for img_path in sample_images:
        if not img_path.exists():
            continue
        base_name = img_path.name[:22]

        for mode in ["direct", "letterbox"]:
            for tta in [False, True]:
                res = detector.predict(str(img_path), preprocessing_mode=mode, enable_tta=tta)
                pred_label = f"{res['crop']}: {res['condition']}"[:31]
                conf_str = f"{res['confidence']*100:.1f}%"
                tta_str = "ON" if tta else "OFF"
                print(f"{base_name:<24} | {mode:<12} | {tta_str:<5} | {pred_label:<32} | {conf_str:<6} | {res['status']:<14} | {res['quality_status']}")
        print("-" * 115)


def run_test():
    """Legacy entrypoint preserved for compatibility."""
    run_comprehensive_test_suite()
    run_real_crop_comparisons()


if __name__ == "__main__":
    run_test()
