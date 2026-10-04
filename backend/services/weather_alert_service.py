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
        
        # 1. Rain and Heavy Rain Detection
        max_rain_prob = 0
        max_rain_prob_time = None
        max_rain_mm = 0
        max_rain_time = None
        
        for i in range(check_hours):
            if precip_probs and precip_probs[i] > max_rain_prob:
                max_rain_prob = precip_probs[i]
                max_rain_prob_time = times[i]
            if precips and precips[i] > max_rain_mm:
                max_rain_mm = precips[i]
                max_rain_time = times[i]
                
        if max_rain_mm >= thresh.HEAVY_RAIN_MM:
            # Heavy rain
            alerts.append({
                "type": "rain",
                "level": "WARNING",
                "title_en": "Heavy rain expected",
                "title_ta": "கனமழை எதிர்பார்க்கப்படுகிறது",
                "message_en": f"Significant rainfall ({max_rain_mm}mm) is forecast. Check field drainage and avoid unnecessary irrigation.",
                "message_ta": f"குறிப்பிடத்தக்க மழை ({max_rain_mm}mm) எதிர்பார்க்கப்படுகிறது. வடிகால் வசதிகளை சரிபார்க்கவும், தேவையற்ற நீர்ப்பாசனத்தை தவிர்க்கவும்.",
                "start": max_rain_time,
                "probability": max_rain_prob,
                "rain_mm": max_rain_mm,
                "source": "Open-Meteo forecast"
            })
        elif max_rain_prob >= thresh.RAIN_PROBABILITY_HIGH:
            alerts.append({
                "type": "rain",
                "level": "HIGH",
                "title_en": "High chance of rain",
                "title_ta": "மழை பெய்ய அதிக வாய்ப்பு உள்ளது",
                "message_en": "High probability of rain is forecast. Avoid unnecessary irrigation and plan harvesting or spraying activities carefully.",
                "message_ta": "மழை பெய்ய அதிக வாய்ப்பு உள்ளது. தேவையற்ற நீர்ப்பாசனத்தை தவிர்க்கவும், மற்றும் தெளிக்கும் பணிகளை கவனமாக திட்டமிடவும்.",
                "start": max_rain_prob_time,
                "probability": max_rain_prob,
                "source": "Open-Meteo forecast"
            })
        elif max_rain_prob >= thresh.RAIN_PROBABILITY_WARNING:
            alerts.append({
                "type": "rain",
                "level": "ADVISORY",
                "title_en": "Rain likely",
                "title_ta": "மழை பெய்ய வாய்ப்பு உள்ளது",
                "message_en": "Rain is likely in your area. Consider postponing spraying if rain is expected soon.",
                "message_ta": "உங்கள் பகுதியில் மழை பெய்ய வாய்ப்புள்ளது. மழை எதிர்பார்க்கப்பட்டால் தெளிக்கும் பணிகளை தள்ளிவைக்க கருதுங்கள்.",
                "start": max_rain_prob_time,
                "probability": max_rain_prob,
                "source": "Open-Meteo forecast"
            })
            
        # 2. Thunderstorm Detection
        storm_detected = False
        storm_time = None
        has_hail = False
        for i in range(check_hours):
            code = weather_codes[i] if weather_codes else 0
            if code in thresh.THUNDERSTORM_CODES:
                storm_detected = True
                storm_time = times[i]
                if code in thresh.HAIL_CODES:
                    has_hail = True
                break
                
        if storm_detected:
            if has_hail:
                alerts.append({
                    "type": "thunderstorm",
                    "level": "HIGH",
                    "title_en": "Hail risk",
                    "title_ta": "ஆலங்கட்டி மழை அபாயம்",
                    "message_en": "Hail is indicated in the forecast. Protect vulnerable crops where possible and avoid outdoor work during the event.",
                    "message_ta": "வானிலையில் ஆலங்கட்டி மழை கணிக்கப்பட்டுள்ளது. பாதுகாப்பற்ற பயிர்களை பாதுகாக்கவும், திறந்தவெளியில் வேலை செய்வதை தவிர்க்கவும்.",
                    "start": storm_time,
                    "source": "Open-Meteo forecast"
                })
            else:
                alerts.append({
                    "type": "thunderstorm",
                    "level": "WARNING",
                    "title_en": "Thunderstorm warning",
                    "title_ta": "இடியுடன் கூடிய மழை எச்சரிக்கை",
                    "message_en": "Thunderstorm conditions are forecast for your area. Avoid field work during the storm and move to a safe place.",
                    "message_ta": "உங்கள் பகுதியில் இடியுடன் கூடிய மழை பெய்ய வாய்ப்புள்ளது. இந்த நேரத்தில் வயலில் வேலை செய்வதை தவிர்க்கவும்.",
                    "start": storm_time,
                    "source": "Open-Meteo forecast"
                })
                
        # 3. Wind Detection
        max_wind = 0
        max_wind_time = None
        max_gust = 0
        max_gust_time = None
        for i in range(check_hours):
            if wind_speeds and wind_speeds[i] > max_wind:
                max_wind = wind_speeds[i]
                max_wind_time = times[i]
            if wind_gusts and wind_gusts[i] > max_gust:
                max_gust = wind_gusts[i]
                max_gust_time = times[i]
                
        if max_gust >= thresh.WIND_GUSTS_WARNING:
            alerts.append({
                "type": "wind",
                "level": "WARNING",
                "title_en": "High wind gusts",
                "title_ta": "பலத்த காற்று வீசும் எச்சரிக்கை",
                "message_en": "High wind gusts are forecast. Take precautions for vulnerable crops and structures.",
                "message_ta": "பலத்த காற்று வீசும் என கணிக்கப்பட்டுள்ளது. பலவீனமான பயிர்கள் மற்றும் அமைப்புகளுக்கு தகுந்த பாதுகாப்பு எடுக்கவும்.",
                "start": max_gust_time,
                "wind_speed": max_gust,
                "source": "Open-Meteo forecast"
            })
        elif max_wind >= thresh.WIND_SPEED_WARNING:
            alerts.append({
                "type": "wind",
                "level": "WARNING",
                "title_en": "Strong wind warning",
                "title_ta": "பலத்த காற்று எச்சரிக்கை",
                "message_en": "Strong winds are forecast. Avoid spraying during strong winds and check vulnerable crops/support structures.",
                "message_ta": "பலத்த காற்று எதிர்பார்க்கப்படுகிறது. காற்று வீசும் போது மருந்து தெளிப்பதைத் தவிர்க்கவும்.",
                "start": max_wind_time,
                "wind_speed": max_wind,
                "source": "Open-Meteo forecast"
            })
            
        # 4. Extreme Heat
        max_temp = 0
        max_temp_time = None
        for i in range(check_hours):
            if temps and temps[i] > max_temp:
                max_temp = temps[i]
                max_temp_time = times[i]
                
        if max_temp >= thresh.TEMP_HIGH:
            alerts.append({
                "type": "heat",
                "level": "WARNING",
                "title_en": "Heat warning",
                "title_ta": "அதிக வெப்பநிலை எச்சரிக்கை",
                "message_en": "High temperature is forecast. Monitor crops for heat stress and water demand.",
                "message_ta": "அதிக வெப்பநிலை எதிர்பார்க்கப்படுகிறது. பயிர்களில் வெப்ப அழுத்தம் உள்ளதா என கண்காணிக்கவும்.",
                "start": max_temp_time,
                "temperature": max_temp,
                "source": "Open-Meteo forecast"
            })
            
        # 5. High Humidity
        max_humid = 0
        max_humid_time = None
        for i in range(check_hours):
            if humidities and humidities[i] > max_humid:
                max_humid = humidities[i]
                max_humid_time = times[i]
                
        if max_humid >= thresh.HUMIDITY_HIGH:
            # Check for disease linkage
            if condition and "healthy" not in condition.lower():
                alerts.append({
                    "type": "humidity",
                    "level": "ADVISORY",
                    "title_en": "Crop Health + Weather Advisory",
                    "title_ta": "பயிர் ஆரோக்கியம் மற்றும் வானிலை ஆலோசனை",
                    "message_en": "Current weather conditions may favor fungal disease development. Monitor the affected leaves closely and follow appropriate crop-management guidance.",
                    "message_ta": "தற்போதைய வானிலை பூஞ்சை நோய்களின் வளர்ச்சிக்கு சாதகமாக இருக்கலாம். பாதிக்கப்பட்ட இலைகளை உன்னிப்பாகக் கண்காணிக்கவும்.",
                    "start": max_humid_time,
                    "humidity": max_humid,
                    "source": "Open-Meteo forecast"
                })
            else:
                alerts.append({
                    "type": "humidity",
                    "level": "INFO",
                    "title_en": "High humidity",
                    "title_ta": "அதிக ஈரப்பதம்",
                    "message_en": "High humidity may increase conditions favorable to some fungal diseases. Monitor crop leaves closely.",
                    "message_ta": "அதிக ஈரப்பதம் சில பூஞ்சை நோய்களுக்கு சாதகமான சூழ்நிலையை அதிகரிக்கும். பயிர் இலைகளை கண்காணிக்கவும்.",
                    "start": max_humid_time,
                    "humidity": max_humid,
                    "source": "Open-Meteo forecast"
                })
                
        # 6. Crop specific override check
        if crop:
            for alert in alerts:
                if alert["type"] == "rain" and alert["level"] in ["WARNING", "HIGH"]:
                    alert["title_en"] = f"{crop} Weather Advisory"
                    alert["title_ta"] = f"{crop} வானிலை ஆலோசனை"
                    if crop.lower() == "paddy":
                        alert["message_en"] = "Heavy rainfall is forecast. Monitor field water levels and drainage."
                        alert["message_ta"] = "கனமழை கணிக்கப்பட்டுள்ளது. வயலில் நீர் மட்டம் மற்றும் வடிகால் வசதிகளை கண்காணிக்கவும்."
                        
        return alerts
