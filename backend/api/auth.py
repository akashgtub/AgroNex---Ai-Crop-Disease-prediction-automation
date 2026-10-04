from fastapi import APIRouter, Depends, HTTPException, status
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
