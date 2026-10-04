"""
AgroNex Unit Tests for Crop Taxonomy and Hierarchical Mapping
Tests taxonomy completeness, indexing consistency, probability aggregation, and renormalization.
"""

import sys
import unittest
from pathlib import Path
import numpy as np

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from evaluation.experimental.crop_mapping import CropTaxonomy


class TestCropTaxonomy(unittest.TestCase):
    """Test suite for crop mapping and hierarchical probability operations."""

    def setUp(self):
        self.taxonomy = CropTaxonomy()

    def test_taxonomy_completeness(self):
        """Verify all 38 classes are present and map to 14 crops."""
        self.assertEqual(self.taxonomy.num_classes, 38)
        self.assertEqual(self.taxonomy.num_crops, 14)
        expected_crops = [
            "Apple", "Blueberry", "Cherry_(including_sour)", "Corn_(maize)",
            "Grape", "Orange", "Peach", "Pepper,_bell", "Potato",
            "Raspberry", "Soybean", "Squash", "Strawberry", "Tomato"
        ]
        self.assertEqual(self.taxonomy.crops, sorted(expected_crops))

    def test_class_partition(self):
        """Verify the union of all crop classes forms a complete partition of 0..37."""
        all_indices = set()
        for crop in self.taxonomy.crops:
            crop_indices = self.taxonomy.get_crop_classes(crop)
            # Ensure no overlapping indices across crops
            self.assertTrue(all_indices.isdisjoint(set(crop_indices)))
            all_indices.update(crop_indices)

        self.assertEqual(all_indices, set(range(38)))

    def test_crop_lookup_consistency(self):
        """Verify integer and string lookups yield identical crop names."""
        for idx, class_name in enumerate(self.taxonomy.classes):
            crop_by_idx = self.taxonomy.get_crop(idx)
            crop_by_name = self.taxonomy.get_crop(class_name)
            self.assertEqual(crop_by_idx, crop_by_name)
            self.assertEqual(crop_by_idx, class_name.split("___")[0])

    def test_aggregate_crop_probabilities(self):
        """Verify sum-aggregation of probabilities across crops preserves total mass."""
        # Create a valid probability distribution summing to 1.0
        rng = np.random.RandomState(42)
        raw = rng.uniform(0.1, 1.0, size=38)
        probs = raw / np.sum(raw)

        crop_probs = self.taxonomy.aggregate_crop_probabilities(probs)
        self.assertEqual(len(crop_probs), 14)
        total_mass = sum(crop_probs.values())
        self.assertAlmostEqual(total_mass, 1.0, places=6)

        # Check Tomato specifically
        tomato_indices = self.taxonomy.get_crop_classes("Tomato")
        expected_tomato_mass = float(np.sum(probs[tomato_indices]))
        self.assertAlmostEqual(crop_probs["Tomato"], expected_tomato_mass, places=6)

    def test_renormalize_for_crop(self):
        """Verify within-crop renormalization sums to 1.0 and masks out-of-crop classes."""
        probs = np.zeros(38, dtype=np.float32)
        # Assign probabilities to Apple classes
        apple_indices = self.taxonomy.get_crop_classes("Apple")  # [0, 1, 2, 3]
        probs[0] = 0.10  # Apple scab
        probs[1] = 0.20  # Apple black rot
        probs[2] = 0.05  # Cedar apple rust
        probs[3] = 0.15  # Apple healthy
        # Spurious class from another crop
        probs[26] = 0.50  # Strawberry leaf scorch (highest flat probability)

        best_idx, best_conf, masked_38 = self.taxonomy.renormalize_for_crop(probs, "Apple")

        # Best disease in Apple is Apple black rot (idx 1, with 0.20 out of 0.50 Apple total)
        self.assertEqual(best_idx, 1)
        # Renormalized confidence = 0.20 / (0.10 + 0.20 + 0.05 + 0.15) = 0.20 / 0.50 = 0.40
        self.assertAlmostEqual(best_conf, 0.40, places=5)

        # Non-apple classes must have 0.0 in masked vector
        self.assertEqual(masked_38[26], 0.0)
        # Masked vector must sum to 1.0
        self.assertAlmostEqual(float(np.sum(masked_38)), 1.0, places=5)

    def test_hierarchical_decision_flip(self):
        """
        Verify that when probability is fragmented across multiple diseases of a crop,
        crop aggregation correctly prioritizes that crop over an isolated spurious class.
        """
        probs = np.zeros(38, dtype=np.float32)
        # Isolated high class: Strawberry leaf scorch (idx 26) = 0.35
        probs[26] = 0.35

        # Tomato classes each lower than 0.35, but together sum to 0.45:
        probs[28] = 0.15  # Tomato bacterial spot
        probs[29] = 0.15  # Tomato early blight
        probs[30] = 0.15  # Tomato late blight
        # Rest: uniform small mass
        remaining = 1.0 - (0.35 + 0.45)
        probs[0:20] += remaining / 20.0

        # Flat argmax gives Strawberry (idx 26)
        flat_pred = int(np.argmax(probs))
        self.assertEqual(flat_pred, 26)

        # Crop aggregation gives Tomato (0.45 > 0.35)
        crop_probs = self.taxonomy.aggregate_crop_probabilities(probs)
        best_crop = max(crop_probs.keys(), key=lambda c: crop_probs[c])
        self.assertEqual(best_crop, "Tomato")

        # Within-crop constraint picks top Tomato disease
        best_disease, _, _ = self.taxonomy.renormalize_for_crop(probs, "Tomato")
        self.assertIn(best_disease, [28, 29, 30])
        self.assertNotEqual(best_disease, 26)


if __name__ == "__main__":
    unittest.main()
