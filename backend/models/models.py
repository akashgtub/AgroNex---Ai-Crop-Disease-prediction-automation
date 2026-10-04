from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from config.database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    mobile = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    location = Column(String, nullable=True)
    preferred_language = Column(String, default="en")
    
    profile = relationship("FarmerProfile", back_populates="user", uselist=False)
    analyses = relationship("CropAnalysis", back_populates="user")

class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    farm_size = Column(Float, nullable=True) # in acres
    primary_crop = Column(String, nullable=True)
    
    user = relationship("User", back_populates="profile")

class CropAnalysis(Base):
    __tablename__ = "crop_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    crop_type = Column(String)
    image_path = Column(String)
    detected_disease = Column(String)
    confidence = Column(Float)
    severity = Column(String)
    risk_level = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="analyses")

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String) # 'user' or 'ai'
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
