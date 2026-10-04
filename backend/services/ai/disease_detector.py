import json
import numpy as np
import onnxruntime as ort
from PIL import Image
import os
from pathlib import Path

class DiseaseDetector:
    def __init__(self):
        # Paths
        base_dir = Path(__file__).resolve().parent.parent.parent
        model_dir = base_dir / 'models'
        
        self.model_path = str(model_dir / 'efficientnet_v2_s_best.onnx')
        self.classes_path = str(model_dir / 'classes.json')
        
        # Load classes and normalisation config
        with open(self.classes_path, 'r') as f:
            self.config = json.load(f)
            
        self.classes = self.config['classes']
        self.img_size = self.config['image_size']
        self.mean = np.array(self.config['normalisation']['mean'], dtype=np.float32)
        self.std = np.array(self.config['normalisation']['std'], dtype=np.float32)
        
        # Load ONNX session
        self.session = ort.InferenceSession(self.model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
    def _preprocess(self, image_path: str) -> np.ndarray:
        # Load image
        img = Image.open(image_path).convert('RGB')
        
        # Resize to match training (usually resize shortest side to img_size or larger, then center crop)
        # Resize directly to 224x224 using Bilinear interpolation
        img = img.resize((self.img_size, self.img_size), Image.Resampling.BILINEAR)
        
        # Convert to numpy array [0, 1]
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        # Normalize
        img_array = (img_array - self.mean) / self.std
        
        # Transpose to Channel, Height, Width (C, H, W)
        img_array = np.transpose(img_array, (2, 0, 1))
        
        # Add batch dimension (B, C, H, W)
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
        
    def _softmax(self, x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=1, keepdims=True)

    def predict(self, image_path: str):
        # Preprocess
        input_data = self._preprocess(image_path)
        
        print("\n=== MODEL DEBUG INFORMATION ===")
        print(f"Model: {os.path.basename(self.model_path)}")
        print(f"Input: {input_data.shape[0]} x {input_data.shape[1]} x {input_data.shape[2]} x {input_data.shape[3]}")
        
        # Inference
        outputs = self.session.run([self.output_name], {self.input_name: input_data})
        logits = outputs[0]
        
        # Softmax probabilities
        probs = self._softmax(logits)[0]
        
        # Get top 5 predictions
        top_k_indices = np.argsort(probs)[::-1][:5]
        
        top_predictions = []
        print("\nTop 5 predictions:")
        for idx_rank, idx in enumerate(top_k_indices):
            class_name = self.classes[idx]
            confidence = float(probs[idx])
            top_predictions.append({
                "class_name": class_name,
                "confidence": confidence
            })
            if idx_rank < 5:
                print(f"{idx_rank + 1}. {class_name} — {confidence*100:.1f}%")
        print("===============================\n")
            
        best_prediction = top_predictions[0]
        class_name = best_prediction["class_name"]
        confidence = best_prediction["confidence"]
        
        # Parse crop and condition from class name e.g., "Tomato___Early_blight"
        parts = class_name.split('___')
        crop = parts[0].replace('_', ' ') if len(parts) > 0 else "Unknown"
        condition = parts[1].replace('_', ' ') if len(parts) > 1 else class_name
        
        is_healthy = 'healthy' in condition.lower()
        
        conf_percent = confidence * 100
        if conf_percent >= 80:
            status = "High confidence"
        elif conf_percent >= 60:
            status = "Moderate confidence"
        else:
            status = "Uncertain"
            condition = "AgroNex is not confident about this result. Please upload a clearer image."
            is_healthy = False # Ensure we don't show green healthy UI for uncertain
        
        return {
            "crop": crop,
            "condition": condition,
            "confidence": confidence,
            "is_healthy": is_healthy,
            "top_predictions": top_predictions,
            # Keeping backwards compatibility with old mock format
            "disease": condition,
            "severity": "Not determined",
            "risk": "Not determined",
            "status": status
        }
