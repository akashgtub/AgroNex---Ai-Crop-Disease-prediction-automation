
import json
import numpy as np
import onnxruntime as ort
from PIL import Image
import os
import sys

def run_test():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(base_dir, 'models')
    model_path = os.path.join(model_dir, 'efficientnet_v2_s_best.onnx')
    classes_path = os.path.join(model_dir, 'classes.json')
    
    test_image_path = os.path.join(base_dir, "test_tomato.png")
    
    print("\n--- Test Configuration ---")
    print(f"Image path: {test_image_path}")
    
    img = Image.open(test_image_path).convert("RGB")
    print(f"Image original size: {img.size}")
    
    # OFFICIAL PREPROCESSING
    img_resized = img.resize((224, 224), Image.Resampling.BILINEAR)
    print(f"Preprocessed size: {img_resized.size}")
    
    arr = (np.array(img_resized, dtype=np.float32) / 255.0 - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    tensor = np.expand_dims(np.transpose(arr, (2, 0, 1)), axis=0).astype(np.float32)
    
    # INFERENCE
    session = ort.InferenceSession(model_path)
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    
    outputs = session.run([output_name], {input_name: tensor})
    logits = outputs[0][0]
    
    e_x = np.exp(logits - np.max(logits))
    probs = e_x / e_x.sum()
    
    with open(classes_path, 'r') as f:
        classes = json.load(f)['classes']
        
    sorted_indices = np.argsort(probs)[::-1]
    
    print("\n--- Inference Results ---")
    print(f"Predicted index: {sorted_indices[0]}")
    print(f"Predicted class: {classes[sorted_indices[0]]}")
    
    print("\n--- Top 5 Classes & Probabilities ---")
    for i in range(5):
        idx = sorted_indices[i]
        print(f"[{idx}] {classes[idx]}: {probs[idx]:.4f}")
        
    print("\n--- Complete Top 10 Predictions ---")
    for i in range(10):
        idx = sorted_indices[i]
        print(f"{i+1}. [{idx}] {classes[idx]} ({probs[idx]*100:.2f}%)")

if __name__ == "__main__":
    run_test()
