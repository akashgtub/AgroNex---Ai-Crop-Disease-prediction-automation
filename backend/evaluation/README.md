# AgroNex Plant Disease Model Evaluation Framework

This module provides quantitative evaluation tools for the AgroNex EfficientNetV2-S ONNX model (`efficientnet_v2_s_best.onnx`) across ground-truth datasets.

---

## 1. Important Dataset Clarifications

To maintain scientific integrity, this project strictly distinguishes between three different data contexts:

1. **Training Metadata Validation Score (`99.8895%`)**:
   - The validation accuracy recorded in `backend/models/classes.json` ($904 / 905 \approx 0.998895$) was achieved during laboratory training on the PlantVillage dataset.
   - **This does NOT represent real-world AgroNex field accuracy.** PlantVillage features single leaves on flat studio backgrounds under uniform lighting. In academic literature (*Barbedo et al., 2018*), random splits on PlantVillage frequently exhibit data leakage due to near-duplicate frames of the same leaf.
2. **Repository Sample Images (`backend/uploads/`)**:
   - The sample images in the repository (`grapes - Image.jpeg`, `GrapesImage.jpeg`, `tomoato-Check.jpeg`, `check1.jpeg`) are ad-hoc unannotated files used for frontend UI smoke testing.
   - **They cannot be used as an accuracy benchmark** because they lack verified ground-truth labels.
3. **Future Labeled Field Evaluation Dataset**:
   - Validating the model's true performance in farming conditions requires a dedicated test set collected in outdoor lighting, with natural backgrounds and expert-annotated disease labels.

---

## 2. Evaluation Capabilities

The evaluation engine calculates:
- **Overall Accuracy**: Total correct predictions over total samples.
- **Macro Precision, Recall, and F1**: Unweighted arithmetic mean across all active classes (sensitive to performance on minority classes).
- **Weighted Precision, Recall, and F1**: Class-frequency weighted scores.
- **Per-Class Breakdown**: Precision, Recall, F1, True Positives, False Positives, False Negatives, and Support count for each of the 38 classes.
- **38x38 Confusion Matrix**: Identifies specific inter-class confusions (e.g. Tomato Early Blight vs. Septoria Leaf Spot).
- **Confidence Distribution**: Mean, standard deviation, median, quartiles, and 10-bin histogram.
- **Calibration & Expected Calibration Error (ECE)**: Measures whether model confidence matches empirical correctness across probability bins.
- **Latency Tracking**: Measures average, median (p50), and 95th percentile (p95) execution times in milliseconds.

---

## 3. Supported Dataset Formats

### Format A: Directory Structure (ImageFolder)
Organize images into subdirectories named after the exact 38 class names:
```
my_evaluation_dataset/
├── Tomato___Early_blight/
│   ├── leaf_001.jpg
│   └── leaf_002.jpg
├── Corn_(maize)___Common_rust_/
│   ├── leaf_003.jpg
│   └── leaf_004.jpg
└── Grape___healthy/
    └── leaf_005.jpg
```

### Format B: CSV Manifest
A `.csv` file containing file paths and ground-truth class labels:
```csv
image_path,label
/path/to/images/leaf1.jpg,Tomato___Early_blight
/path/to/images/leaf2.jpg,Corn_(maize)___healthy
```
*(Relative image paths in the CSV will be resolved relative to the CSV file location).*

### Format C: JSONL Manifest
A `.jsonl` file with one JSON object per line:
```json
{"image_path": "path/to/leaf1.jpg", "label": "Tomato___Early_blight"}
{"image_path": "path/to/leaf2.jpg", "label": "Corn_(maize)___healthy"}
```

---

## 4. Usage Instructions

### Run the Evaluation Pipeline Self-Test (Synthetic Fixture)
To verify the entire evaluation harness without downloading external datasets:
```bash
python backend/evaluation/evaluate.py --run-test-fixture
```

### Evaluate on a Custom Labeled Dataset
```bash
# Evaluate using baseline direct resize
python backend/evaluation/evaluate.py --data-path /path/to/dataset --mode direct

# Evaluate using letterbox padding (aspect-preserving)
python backend/evaluation/evaluate.py --data-path /path/to/dataset --mode letterbox

# Evaluate with multi-view Test-Time Augmentation (TTA)
python backend/evaluation/evaluate.py --data-path /path/to/dataset --mode direct --enable-tta
```

### Run Side-by-Side Strategy Comparison
To compare `direct`, `letterbox`, and `TTA` on the exact same dataset:
```bash
python backend/evaluation/evaluate.py --data-path /path/to/dataset --compare-all
```

---

## 5. Output Artifacts

Running evaluation generates:
1. **Console Summary**: Clean summary tables showing global metrics, confidence distribution, and top classes by support.
2. **`evaluation_results.json`**: Complete structured JSON report containing metadata, metrics, calibration bins, latency percentiles, and the full $38 \times 38$ confusion matrix.
3. **`per_class_metrics.csv`**: Tabular CSV report with precision, recall, F1, support, TP, FP, FN, and TN for every class.
