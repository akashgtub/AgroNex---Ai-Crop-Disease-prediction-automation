from datetime import datetime
from typing import List, Dict, Any
from config import weather_thresholds as thresh

class WeatherAlertService:
    def generate_alerts(self, forecast: Dict[str, Any], crop: str = None, condition: str = None) -> List[Dict[str, Any]]:
        alerts = []
        
        # We look ahead for the next 24-48 hours
        hourly = forecast.get("hourly", {})
        times = hourly.get("time", [])
        
        if not times:
            return alerts
            
        precip_probs = hourly.get("precipitation_probability", [])
        precips = hourly.get("precipitation", [])
        weather_codes = hourly.get("weather_code", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_gusts = hourly.get("wind_gusts_10m", [])
        temps = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        
        # Only check the first 24 hours
        check_hours = min(24, len(times))
        
        def get_time_of_day(iso_time_str):
            if not iso_time_str:
                return "today"
            try:
                dt = datetime.fromisoformat(iso_time_str)
                hour = dt.hour
                if 5 <= hour < 12: return "morning"
                elif 12 <= hour < 17: return "afternoon"
                elif 17 <= hour < 21: return "evening"
                else: return "night"
            except:
                return "today"
                
        def get_time_of_day_ta(iso_time_str):
            if not iso_time_str:
                return "இன்று"
            try:
                dt = datetime.fromisoformat(iso_time_str)
                hour = dt.hour
                if 5 <= hour < 12: return "காலை"
                elif 12 <= hour < 17: return "பிற்பகல்"
                elif 17 <= hour < 21: return "மாலை"
                else: return "இரவு"
            except:
                return "இன்று"

        # 1. Rain Detection
        max_rain_prob = 0
        max_rain_prob_time = None
        
        for i in range(check_hours):
            if precip_probs and precip_probs[i] > max_rain_prob:
                max_rain_prob = precip_probs[i]
                max_rain_prob_time = times[i]
                
        if max_rain_prob >= 70:
            tod_en = get_time_of_day(max_rain_prob_time)
            tod_ta = get_time_of_day_ta(max_rain_prob_time)
            alerts.append({
                "type": "rain",
                "level": "HIGH",
                "title_en": "High Chance of Rain",
                "title_ta": "மழை பெய்ய அதிக வாய்ப்பு உள்ளது",
                "message_en": f"Rain is likely around {tod_en}. Consider planning irrigation and field activities accordingly.",
                "message_ta": f"{tod_ta} நேரத்தில் மழை பெய்ய வாய்ப்புள்ளது. அதற்கேற்ப நீர்ப்பாசனம் மற்றும் களப்பணிகளைத் திட்டமிடுங்கள்.",
                "start": max_rain_prob_time,
                "probability": max_rain_prob,
                "source": "Open-Meteo forecast"
            })
            
        # 2. Thunderstorm Detection (Based strictly on WMO codes)
        storm_detected = False
        storm_time = None
        has_hail = False
        for i in range(check_hours):
            code = weather_codes[i] if weather_codes else 0
            if code in [95, 96, 99]:
                storm_detected = True
                storm_time = times[i]
                if code in [96, 99]:
                    has_hail = True
                break
                
        if storm_detected:
            tod_en = get_time_of_day(storm_time)
            tod_ta = get_time_of_day_ta(storm_time)
            if has_hail:
                alerts.append({
                    "type": "thunderstorm",
                    "level": "HIGH",
                    "title_en": "Severe Weather Alert (Hail)",
                    "title_ta": "கடுமையான வானிலை (ஆலங்கட்டி மழை)",
                    "message_en": f"Hail and thunderstorms are indicated around {tod_en}. Protect vulnerable crops where possible.",
                    "message_ta": f"{tod_ta} நேரத்தில் ஆலங்கட்டி மற்றும் இடியுடன் கூடிய மழை பெய்யும். பலவீனமான பயிர்களைப் பாதுகாக்கவும்.",
                    "start": storm_time,
                    "source": "Open-Meteo forecast"
                })
            else:
                alerts.append({
                    "type": "thunderstorm",
                    "level": "WARNING",
                    "title_en": "Thunderstorm Warning",
                    "title_ta": "இடியுடன் கூடிய மழை எச்சரிக்கை",
                    "message_en": f"Thunderstorm conditions are forecast around {tod_en}. Avoid field work during the storm.",
                    "message_ta": f"{tod_ta} நேரத்தில் இடியுடன் கூடிய மழைக்கு வாய்ப்புள்ளது. வயல்வெளியில் வேலை செய்வதைத் தவிர்க்கவும்.",
                    "start": storm_time,
                    "source": "Open-Meteo forecast"
                })
                
        return alerts
