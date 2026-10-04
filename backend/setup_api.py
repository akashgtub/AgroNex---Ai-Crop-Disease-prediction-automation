import os

api_dir = "c:/AgroNex/backend/api"
os.makedirs(api_dir, exist_ok=True)

files = {
    "__init__.py": "",
    "auth.py": """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from config.database import get_db
from schemas import schemas

router = APIRouter()

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return {"id": 1, "name": user.name, "mobile": user.mobile, "email": user.email, "location": user.location, "preferred_language": user.preferred_language}

@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    return {"access_token": "fake-token", "token_type": "bearer", "user": {"id": 1, "name": "Test Farmer"}}
""",
    "crops.py": """from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from schemas import schemas
from services.ai.disease_detector import DiseaseDetector
from datetime import datetime

router = APIRouter()
detector = DiseaseDetector()

@router.post("/analyze", response_model=schemas.CropAnalysisResponse)
async def analyze_crop(
    crop_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Mock file save
    file_path = f"uploads/{file.filename}"
    
    # Use AI service
    prediction = detector.predict(file_path)
    
    return {
        "id": 1,
        "crop_type": crop_type,
        "image_path": file_path,
        "detected_disease": prediction["disease"],
        "confidence": prediction["confidence"],
        "severity": prediction["severity"],
        "risk_level": prediction["risk"],
        "created_at": datetime.now()
    }

@router.get("/history", response_model=List[schemas.CropAnalysisResponse])
def get_history(db: Session = Depends(get_db)):
    return [
        {
            "id": 1,
            "crop_type": "Tomato",
            "image_path": "uploads/mock.jpg",
            "detected_disease": "Early Blight",
            "confidence": 0.94,
            "severity": "Moderate",
            "risk_level": "High",
            "created_at": datetime.now()
        }
    ]
""",
    "assistant.py": """from fastapi import APIRouter, Depends
from schemas import schemas
from services.ai.ai_assistant import AIAssistant

router = APIRouter()
assistant = AIAssistant()

@router.post("/chat", response_model=schemas.ChatResponse)
def chat(message: schemas.ChatMessage):
    reply = assistant.answer(message.message, message.language, {})
    return {"reply": reply}
""",
    "profile.py": """from fastapi import APIRouter, Depends
from schemas import schemas

router = APIRouter()

@router.get("/")
def get_profile():
    return {"name": "Test Farmer", "mobile": "1234567890", "location": "Tamil Nadu", "farm_size": 5, "primary_crop": "Paddy"}
""",
    "weather.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_weather():
    return {
        "temperature": 28,
        "condition": "Partly Cloudy",
        "humidity": 72,
        "rain_probability": 60,
        "advisory": "High humidity may increase the risk of fungal disease. Monitor your crop carefully."
    }
""",
    "schemes.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_schemes():
    return [
        {
            "id": 1,
            "name": "PM-KISAN",
            "who_can_apply": "Small and marginal farmers",
            "benefits": "₹6000 per year",
            "eligibility": "Landholding up to 2 hectares",
            "source": "https://pmkisan.gov.in/"
        }
    ]
"""
}

for name, content in files.items():
    with open(os.path.join(api_dir, name), "w", encoding="utf-8") as f:
        f.write(content)

services_dir = "c:/AgroNex/backend/services/ai"
os.makedirs(services_dir, exist_ok=True)

ai_files = {
    "__init__.py": "",
    "disease_detector.py": """class DiseaseDetector:
    def predict(self, image_path: str):
        # Mock implementation
        return {
            "disease": "Early Blight",
            "confidence": 0.94,
            "severity": "Moderate",
            "risk": "High"
        }
""",
    "ai_assistant.py": """class AIAssistant:
    def answer(self, question: str, language: str, context: dict):
        if language == "ta":
            return "இது ஒரு மாதிரி பதில். (This is a mock response)."
        return "This is a mock response from AgroNex AI. You asked: " + question
"""
}

for name, content in ai_files.items():
    with open(os.path.join(services_dir, name), "w", encoding="utf-8") as f:
        f.write(content)
