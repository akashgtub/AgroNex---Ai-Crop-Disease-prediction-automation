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
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
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
            daily = data.get("daily", {})
            alerts = self.alert_service.generate_alerts(data, crop, condition)

            # Map weather code
            code = current.get("weather_code", 0)
            condition_en = "Clear"
            condition_ta = "தெளிவான"
            if code in [1, 2, 3]:
                condition_en, condition_ta = "Partly Cloudy", "பகுதி மேகமூட்டம்"
            elif code in [45, 48]:
                condition_en, condition_ta = "Foggy", "மூடுபனி"
            elif code in [51, 53, 55, 56, 57]:
                condition_en, condition_ta = "Drizzle", "தூறல்"
            elif code in [61, 63, 65, 66, 67, 80, 81, 82]:
                condition_en, condition_ta = "Rain", "மழை"
            elif code in [95, 96, 99]:
                condition_en, condition_ta = "Thunderstorm", "இடியுடன் கூடிய மழை"
            
            # Format 7-day forecast
            forecast = []
            if "time" in daily:
                for i in range(len(daily["time"])):
                    forecast.append({
                        "date": daily["time"][i],
                        "temperature_max": daily["temperature_2m_max"][i],
                        "temperature_min": daily["temperature_2m_min"][i],
                        "precipitation_probability_mean": daily["precipitation_probability_max"][i],
                    })
            
            return {
                "success": True,
                "location": {
                    "latitude": lat,
                    "longitude": lon
                },
                "condition_en": condition_en,
                "condition_ta": condition_ta,
                "current": {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "precipitation": current.get("precipitation"),
                    "weather_code": code
                },
                "forecast": forecast,
                "alerts": alerts
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": "Weather information is temporarily unavailable.",
                "details": str(e)
            }
