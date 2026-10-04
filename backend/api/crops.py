import os
from fastapi import APIRouter, Depends, UploadFile, File, Form
from supabase import Client
from config.database import get_supabase
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
    db: Client = Depends(get_supabase)
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
        
    # Save the file temporarily
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
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
    print("=================================\n")
    
    # Use AI service
    try:
        prediction = detector.predict(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop analysis failed: {str(e)}")
        
    try:
        # Upload to Supabase Storage
        file_name_in_storage = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
        with open(file_path, "rb") as f:
            # We must use proper kwargs for supabase python client
            res = db.storage.from_("crop-images").upload(file_name_in_storage, f.read(), {"content-type": file.content_type})
            
        public_url = db.storage.from_("crop-images").get_public_url(file_name_in_storage)
        
        # Save to database
        # Assuming a default dummy user_id for now as we don't have full auth setup yet.
        # But we will leave it null if not provided since RLS might not strictly require it in our custom setup
        db_record = {
            "crop_type": prediction["crop"],
            "image_path": public_url,
            "detected_disease": prediction["condition"],
            "confidence": float(prediction["confidence"]),
            "severity": prediction["severity"],
            "risk_level": prediction["risk"]
        }
        
        db.table("crop_analyses").insert(db_record).execute()
        
    except Exception as e:
        print(f"Warning: Failed to save to Supabase: {str(e)}")
        # We still return the prediction even if saving fails
    
    # Optionally remove local file
    try:
        os.remove(file_path)
    except:
        pass
    
    return prediction


