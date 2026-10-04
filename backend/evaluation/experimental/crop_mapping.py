"""
AgroNex Experimental Crop Mapping Module
Provides definitive taxonomy mapping from the 38 AgroNex disease classes to their 14 host crops.
Used for simulated hierarchical (Crop -> Disease) classification experiments.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

# Path to model classes definition
DEFAULT_CLASSES_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "classes.json"


class CropTaxonomy:
    """Manages the hierarchical mapping between crops and disease classes."""

    def __init__(self, classes_path: Optional[Union[str, Path]] = None):
        path = Path(classes_path) if classes_path else DEFAULT_CLASSES_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.classes: List[str] = data["classes"]
        self.num_classes: int = len(self.classes)
        self.class_to_idx: Dict[str, int] = {c: i for i, c in enumerate(self.classes)}

        # Extract 14 unique crop identifiers
        # Format in classes.json is strictly "<CropPrefix>___<DiseaseCondition>"
        self.class_idx_to_crop: Dict[int, str] = {}
        self.crop_to_class_indices: Dict[str, List[int]] = {}
        self.crop_to_class_names: Dict[str, List[str]] = {}

        for idx, class_name in enumerate(self.classes):
            crop_prefix = class_name.split("___")[0]
            self.class_idx_to_crop[idx] = crop_prefix

            if crop_prefix not in self.crop_to_class_indices:
                self.crop_to_class_indices[crop_prefix] = []
                self.crop_to_class_names[crop_prefix] = []

            self.crop_to_class_indices[crop_prefix].append(idx)
            self.crop_to_class_names[crop_prefix].append(class_name)

        self.crops: List[str] = sorted(list(self.crop_to_class_indices.keys()))
        self.num_crops: int = len(self.crops)

    def get_crop(self, class_identifier: Union[int, str, np.integer]) -> str:
        """Returns the host crop name for a given class index or class name."""
        if isinstance(class_identifier, (int, np.integer)):
            idx = int(class_identifier)
            if idx not in self.class_idx_to_crop:
                raise KeyError(f"Invalid class index {idx}. Must be in 0..{self.num_classes - 1}")
            return self.class_idx_to_crop[idx]
        elif isinstance(class_identifier, str):
            if class_identifier not in self.class_to_idx:
                raise KeyError(f"Invalid class name '{class_identifier}'.")
            return self.class_idx_to_crop[self.class_to_idx[class_identifier]]
        raise TypeError(f"Expected int or str, got {type(class_identifier)}")

    def get_crop_classes(self, crop: str) -> List[int]:
        """Returns the list of 38-class indices associated with a crop."""
        if crop not in self.crop_to_class_indices:
            raise KeyError(f"Unknown crop '{crop}'. Valid crops: {self.crops}")
        return self.crop_to_class_indices[crop]

    def aggregate_crop_probabilities(self, probs: np.ndarray) -> Dict[str, float]:
        """
        Sums disease probabilities belonging to each crop:
        P(crop_k) = sum_{d in crop_k} P(disease_d).
        """
        crop_probs = {}
        for crop, indices in self.crop_to_class_indices.items():
            crop_probs[crop] = float(np.sum(probs[indices]))
        return crop_probs

    def renormalize_for_crop(self, probs: np.ndarray, target_crop: str) -> Tuple[int, float, np.ndarray]:
        """
        Constrains probabilities to candidate disease classes belonging to target_crop,
        renormalizes them to sum to 1.0, and returns the top-1 disease index, confidence,
        and full 38-length masked probability distribution.
        """
        allowed_indices = self.get_crop_classes(target_crop)
        allowed_probs = probs[allowed_indices]
        sum_allowed = np.sum(allowed_probs)

        if sum_allowed <= 1e-12:
            # Fallback uniform over allowed classes if all allowed probs are zero
            renorm_allowed = np.full_like(allowed_probs, 1.0 / len(allowed_indices))
        else:
            renorm_allowed = allowed_probs / sum_allowed

        best_local_idx = int(np.argmax(renorm_allowed))
        best_global_idx = allowed_indices[best_local_idx]
        best_confidence = float(renorm_allowed[best_local_idx])

        # Create masked 38-vector with 0 for unallowed classes
        masked_38 = np.zeros_like(probs)
        masked_38[allowed_indices] = renorm_allowed

        return best_global_idx, best_confidence, masked_38
