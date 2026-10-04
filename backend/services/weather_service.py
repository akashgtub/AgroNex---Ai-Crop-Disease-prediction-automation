import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Tuple
from services.weather_alert_service import WeatherAlertService

class WeatherService:
    def __init__(self):
        self.alert_service = WeatherAlertService()
        
    def get_weather(self, lat: float, lon: float, crop: str = None, condition: str = None) -> Dict[str, Any]:
        # Open-Meteo API endpoint
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        # Parameters requested
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
            "timezone": "auto",
            "forecast_days": 7
        }
        
        query_string = urllib.parse.urlencode(params, doseq=True)
        url = f"{base_url}?{query_string}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AgroNex/1.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            current = data.get("current", {})
            alerts = self.alert_service.generate_alerts(data, crop, condition)
            
            return {
                "success": True,
                "location": {
                    "latitude": lat,
                    "longitude": lon
                },
                "current": {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "precipitation": current.get("precipitation"),
                    "weather_code": current.get("weather_code")
                },
                "alerts": alerts
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": "Weather information is temporarily unavailable.",
                "details": str(e)
            }
