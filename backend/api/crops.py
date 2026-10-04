import os
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from schemas import schemas
from services.ai.disease_detector import DiseaseDetector
from datetime import datetime

from PIL import Image
from fastapi import HTTPException

router = APIRouter()
detector = DiseaseDetector()

@router.post("/analyze", response_model=schemas.CropAnalysisResponse)
async def analyze_crop(
    file: UploadFile = File(...),
    mode: str = Form("direct"),
    enable_tta: bool = Form(False),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
        
    # Save the file temporarily
    os.makedirs("uploads", exist_ok=True)
    filename = os.path.basename(file.filename)
    file_path = f"uploads/{filename}"
    file_bytes = await file.read()
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    try:
        img = Image.open(file_path)
        img_width, img_height = img.size
    except Exception as e:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
        
    file_size_kb = len(file_bytes) / 1024
    
    print("\n=== UPLOADED IMAGE DEBUG INFO ===")
    print(f"Uploaded image:\n{file.filename}")
    print(f"\nContent type:\n{file.content_type}")
    print(f"\nSize:\n{file_size_kb:.1f} KB")
    print(f"\nDimensions:\n{img_width} x {img_height}")
    print(f"\nMode:\n{mode}, TTA: {enable_tta}")
    print("=================================\n")
    
    # Use AI service
    try:
        prediction = detector.predict(file_path, preprocessing_mode=mode, enable_tta=enable_tta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop analysis failed: {str(e)}")
    
    return prediction


