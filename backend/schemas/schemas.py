from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str
    mobile: str
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    preferred_language: Optional[str] = "en"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str # mobile or email
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TopPrediction(BaseModel):
    class_name: str
    confidence: float

class CropAnalysisBase(BaseModel):
    crop_type: str
    detected_disease: str
    confidence: float
    severity: str
    risk_level: str

class CropAnalysisCreate(CropAnalysisBase):
    image_path: str

class CropAnalysisResponse(BaseModel):
    crop: str
    condition: str
    confidence: float
    is_healthy: bool
    status: str
    top_predictions: List[TopPrediction]
    disease: Optional[str] = None
    severity: Optional[str] = "Not determined"
    risk: Optional[str] = "Not determined"
    quality_status: Optional[str] = "Passed"
    warning_message: Optional[str] = None
    uncertainty_reason: Optional[str] = None
    latency_ms: Optional[float] = None
    preprocessing_mode: Optional[str] = "direct"
    tta_enabled: Optional[bool] = False

class ChatMessage(BaseModel):
    message: str
    language: Optional[str] = "en"

class ChatResponse(BaseModel):
    reply: str
