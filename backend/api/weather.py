from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from services.weather_service import WeatherService

router = APIRouter()
weather_service = WeatherService()

@router.get("/")
@router.get("/forecast")
async def get_forecast(
    lat: float = Query(...),
    lon: float = Query(...),
    crop: Optional[str] = None,
    condition: Optional[str] = None
):
    result = weather_service.get_weather(lat, lon, crop, condition)
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error"))
    return result
