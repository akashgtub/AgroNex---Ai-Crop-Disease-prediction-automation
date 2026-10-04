from fastapi import APIRouter, Depends
from schemas import schemas

router = APIRouter()

@router.get("/")
def get_profile():
    return {"name": "Test Farmer", "mobile": "1234567890", "location": "Tamil Nadu", "farm_size": 5, "primary_crop": "Paddy"}
