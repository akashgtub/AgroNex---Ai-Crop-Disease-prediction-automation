import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

# Baseline heuristic threshold constants (configurable defaults to be calibrated against validation datasets)
DEFAULT_QUALITY_CONFIG: Dict[str, Any] = {
    "enable_quality_gate": True,
    "min_image_width": 100,           # Baseline minimum recommended width in pixels
    "min_image_height": 100,          # Baseline minimum recommended height in pixels
    "blur_laplacian_threshold": 60.0, # Baseline focus threshold via discrete Laplacian variance
    "darkness_mean_threshold": 40.0,   # Baseline minimum mean luminance (0-255 scale)
    "overexposure_clip_ratio": 0.25,   # Baseline maximum fraction of pixels with luminance > 245
    "foliage_min_pixel_ratio": 0.05,   # Baseline minimum green foliage pixel ratio
}


class DiseaseDetector:
    def __init__(
        self,
        quality_config: Optional[Dict[str, Any]] = None,
        model_path: Optional[str] = None,
        classes_path: Optional[str] = None
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        model_dir = base_dir / 'models'

        self.model_path = model_path or str(model_dir / 'efficientnet_v2_s_best.onnx')
        self.classes_path = classes_path or str(model_dir / 'classes.json')

        # Load classes and normalisation config
        with open(self.classes_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.classes: List[str] = self.config['classes']
        self.img_size: int = int(self.config['image_size'])
        self.mean: np.ndarray = np.array(self.config['normalisation']['mean'], dtype=np.float32)
        self.std: np.ndarray = np.array(self.config['normalisation']['std'], dtype=np.float32)

        # Configurable quality threshold dictionary
        self.quality_config = dict(DEFAULT_QUALITY_CONFIG)
        if quality_config:
            self.quality_config.update(quality_config)

        # Load ONNX session
        self.session = ort.InferenceSession(self.model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def _load_and_orient_image(self, image_input: Any) -> Image.Image:
        """Loads image, handles EXIF orientation tags, and safely normalizes alpha."""
        if isinstance(image_input, Image.Image):
            img = image_input
        else:
            img = Image.open(image_input)

        # Correct EXIF rotation (common on smartphone cameras)
        img = ImageOps.exif_transpose(img)

        # Handle transparency / alpha channels cleanly
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # Composite over neutral background instead of black
            img = img.convert('RGBA')
            canvas = Image.new('RGB', img.size, (240, 240, 240))
            canvas.paste(img, mask=img.split()[3])
            return canvas

        return img.convert('RGB')

    def check_image_quality(self, img: Image.Image) -> Tuple[str, Optional[str], Dict[str, float]]:
        """
        Evaluates heuristic quality checks: resolution, darkness, overexposure, blur, and foliage.
        Returns (quality_status, warning_message, metrics_dict).
        Does not replace or suppress downstream model diagnosis.
        """
        if not self.quality_config.get("enable_quality_gate", True):
            return "Passed", None, {}

        w, h = img.size
        min_w = self.quality_config["min_image_width"]
        min_h = self.quality_config["min_image_height"]

        # 1. Dimension Check (very small image check)
        if w < min_w or h < min_h:
            msg = (
                f"Original image resolution ({w}x{h}) is below the recommended minimum "
                f"({min_w}x{min_h}). A higher-resolution image is recommended for reliable analysis."
            )
            return "Warning: Low Resolution", msg, {"width": float(w), "height": float(h)}

        arr = np.array(img, dtype=np.float32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

        # Luminance channel Y (ITU-R BT.601)
        lum = 0.299 * r + 0.587 * g + 0.114 * b

        # Exclude uniform white/studio background from glare check if present (common in lab datasets like PlantVillage)
        is_studio_white = (r > 235.0) & (g > 235.0) & (b > 235.0)
        white_ratio = float(np.mean(is_studio_white))
        # If between 15% and 80% is white, it's a leaf on studio background.
        # If > 80% is white, the image itself is blown out / severely overexposed.
        if 0.15 <= white_ratio <= 0.80:
            target_pixels = ~is_studio_white
        else:
            target_pixels = np.ones_like(lum, dtype=bool)

        if np.any(target_pixels):
            mean_lum = float(np.mean(lum[target_pixels]))
            clip_ratio = float(np.mean(lum[target_pixels] > 245.0))
        else:
            mean_lum = float(np.mean(lum))
            clip_ratio = float(np.mean(lum > 245.0))

        # 2. Darkness Check
        dark_thresh = self.quality_config["darkness_mean_threshold"]
        if mean_lum < dark_thresh:
            msg = (
                f"Image appears underexposed (mean luminance {mean_lum:.1f} < {dark_thresh:.1f}). "
                "Better natural lighting is recommended."
            )
            return "Warning: Low Light", msg, {"mean_luminance": mean_lum}

        # 3. Overexposure / Glare Check
        glare_thresh = self.quality_config["overexposure_clip_ratio"]
        if clip_ratio > glare_thresh:
            msg = (
                f"Excessive surface glare/overexposure detected ({clip_ratio * 100:.1f}% clipped pixels). "
                "Avoid harsh direct flash or specular reflections."
            )
            return "Warning: Overexposed", msg, {"clip_ratio": clip_ratio}

        # 4. Blur Detection (2D discrete Laplacian variance)
        blur_thresh = self.quality_config["blur_laplacian_threshold"]
        if lum.shape[0] >= 3 and lum.shape[1] >= 3:
            lap = lum[:-2, 1:-1] + lum[2:, 1:-1] + lum[1:-1, :-2] + lum[1:-1, 2:] - 4.0 * lum[1:-1, 1:-1]
            blur_var = float(np.var(lap))
        else:
            blur_var = 0.0

        if blur_var < blur_thresh:
            msg = (
                f"Image appears out of focus or blurry (Laplacian variance {blur_var:.1f} < {blur_thresh:.1f}). "
                "A sharper photo is recommended."
            )
            return "Warning: Mild Blur", msg, {"blur_variance": blur_var}

        # 5. Foliage Presence Check (Excess Green Index ExG: 2G - R - B)
        foliage_thresh = self.quality_config["foliage_min_pixel_ratio"]
        exg = 2.0 * g - r - b
        foliage_pixels = (exg > 10.0) & (g > 30.0)
        foliage_ratio = float(np.mean(foliage_pixels))

        if foliage_ratio < foliage_thresh:
            msg = (
                f"Low vegetation/foliage detected ({foliage_ratio * 100:.1f}% green pixels). "
                "Ensure the crop leaf fills most of the frame."
            )
            return "Warning: Low Foliage", msg, {"foliage_ratio": foliage_ratio}

        return "Passed", None, {
            "mean_luminance": mean_lum,
            "clip_ratio": clip_ratio,
            "blur_variance": blur_var,
            "foliage_ratio": foliage_ratio
        }

    def _preprocess_image(self, img: Image.Image, mode: str = "direct") -> np.ndarray:
        """
        Transforms a PIL RGB Image into an NCHW normalized float32 numpy array.
        - 'direct': Baseline direct squish resize to (img_size, img_size).
        - 'letterbox': Isotropic aspect-preserving resize with ImageNet-mean canvas padding.
        """
        if mode == "letterbox":
            w, h = img.size
            scale = self.img_size / max(w, h)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))

            resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

            # Canvas filled with ImageNet mean color [124, 116, 104]
            canvas = Image.new("RGB", (self.img_size, self.img_size), (124, 116, 104))
            pad_left = (self.img_size - new_w) // 2
            pad_top = (self.img_size - new_h) // 2
            canvas.paste(resized, (pad_left, pad_top))
            processed_img = canvas
        else:
            # Baseline direct squish resize
            processed_img = img.resize((self.img_size, self.img_size), Image.Resampling.BILINEAR)

        # Convert to numpy array [0.0, 1.0]
        img_array = np.array(processed_img, dtype=np.float32) / 255.0

        # Normalize with model ImageNet mean and std
        img_array = (img_array - self.mean) / self.std

        # Transpose to Channel, Height, Width (C, H, W)
        img_array = np.transpose(img_array, (2, 0, 1))

        # Add batch dimension (1, C, H, W)
        img_array = np.expand_dims(img_array, axis=0)

        return np.ascontiguousarray(img_array, dtype=np.float32)

    def _preprocess(self, image_path: str, mode: str = "direct") -> np.ndarray:
        """Backwards-compatible path preprocessor."""
        img = self._load_and_orient_image(image_path)
        return self._preprocess_image(img, mode=mode)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax computed independently across batch rows (axis=1)."""
        max_x = np.max(x, axis=1, keepdims=True)
        e_x = np.exp(x - max_x)
        return e_x / np.sum(e_x, axis=1, keepdims=True)

    def predict(
        self,
        image_path: Any,
        preprocessing_mode: str = "direct",
        enable_tta: bool = False
    ) -> Dict[str, Any]:
        """
        Executes crop disease prediction with optional quality checking,
        configurable aspect-ratio mode, and optional Test-Time Augmentation (TTA).
        """
        t_start = time.perf_counter()

        # 1. Ingest & orient image
        img = self._load_and_orient_image(image_path)

        # 2. Quality gatekeeper (measured latency)
        t_quality_start = time.perf_counter()
        quality_status, warning_message, _ = self.check_image_quality(img)
        quality_latency_ms = (time.perf_counter() - t_quality_start) * 1000.0

        # 3. Preprocessing (measured latency)
        t_prep_start = time.perf_counter()
        primary_tensor = self._preprocess_image(img, mode=preprocessing_mode)

        if enable_tta:
            # Multi-sample TTA batch: original + horizontal flip
            flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)
            flipped_tensor = self._preprocess_image(flipped_img, mode=preprocessing_mode)
            input_tensor = np.concatenate([primary_tensor, flipped_tensor], axis=0)
        else:
            input_tensor = primary_tensor

        preprocessing_latency_ms = (time.perf_counter() - t_prep_start) * 1000.0

        # 4. Model Inference (measured latency)
        t_inf_start = time.perf_counter()
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})
        inference_latency_ms = (time.perf_counter() - t_inf_start) * 1000.0
        logits = outputs[0]

        # 5. Softmax calculation
        probs = self._softmax(logits)
        if enable_tta:
            # Average probabilities across TTA views
            probs = np.mean(probs, axis=0)
        else:
            probs = probs[0]

        total_latency_ms = (time.perf_counter() - t_start) * 1000.0

        # 6. Rank Top-5 classes
        top_k_indices = np.argsort(probs)[::-1][:5]
        top_predictions = [
            {
                "class_name": self.classes[idx],
                "confidence": float(probs[idx])
            }
            for idx in top_k_indices
        ]

        best_prediction = top_predictions[0]
        class_name = best_prediction["class_name"]
        confidence = best_prediction["confidence"]

        # Parse crop and condition from class name (e.g. "Tomato___Early_blight")
        parts = class_name.split('___')
        crop = parts[0].replace('_', ' ') if len(parts) > 0 else "Unknown"
        condition = parts[1].replace('_', ' ') if len(parts) > 1 else class_name
        is_healthy = 'healthy' in condition.lower()

        # 7. Model-confidence uncertainty threshold check (kept separate from quality warnings)
        conf_percent = confidence * 100.0
        uncertainty_reason: Optional[str] = None

        if conf_percent >= 80.0:
            status = "High confidence"
        elif conf_percent >= 60.0:
            status = "Moderate confidence"
        else:
            status = "Uncertain"
            uncertainty_reason = (
                f"Model confidence ({conf_percent:.1f}%) is below the uncertainty threshold (60.0%)."
            )

        return {
            # Core prediction fields (preserved)
            "crop": crop,
            "condition": condition,
            "confidence": confidence,
            "is_healthy": is_healthy,
            "top_predictions": top_predictions,
            "disease": condition,
            "severity": "Not determined",
            "risk": "Not determined",
            "status": status,

            # Additive diagnostic and quality fields
            "quality_status": quality_status,
            "warning_message": warning_message,
            "uncertainty_reason": uncertainty_reason,
            "latency_ms": round(total_latency_ms, 2),
            "quality_check_latency_ms": round(quality_latency_ms, 3),
            "preprocessing_latency_ms": round(preprocessing_latency_ms, 3),
            "inference_latency_ms": round(inference_latency_ms, 3),
            "preprocessing_mode": preprocessing_mode,
            "tta_enabled": enable_tta
        }
