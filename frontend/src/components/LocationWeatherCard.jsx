import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { MapPin, CloudSun, AlertTriangle, CloudRain, Wind, ThermometerSun, Map, Navigation } from 'lucide-react';
import { useLocation } from '../hooks/useLocation';

export default function LocationWeatherCard() {
  const { t, i18n } = useTranslation();
  const { location, loading: locLoading, error: locError, requestLocation } = useLocation();
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const isTamil = i18n.language === 'ta';

  useEffect(() => {
    if (location && location.latitude && location.longitude) {
      fetchWeather(location.latitude, location.longitude);
    }
  }, [location]);

  const fetchWeather = async (lat, lon) => {
    setWeatherLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/weather/forecast?lat=${lat}&lon=${lon}`);
      if (!response.ok) throw new Error("Weather API failed");
      const data = await response.json();
      setWeather(data);
    } catch (err) {
      console.error(err);
    } finally {
      setWeatherLoading(false);
    }
  };

  if (locLoading) {
    return (
      <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex items-center justify-center min-h-[160px]">
        <div className="w-6 h-6 border-2 border-green-200 border-t-green-600 rounded-full animate-spin"></div>
        <span className="ml-3 text-gray-500 font-medium">Detecting location...</span>
      </div>
    );
  }

  if (locError) {
    return (
      <div className="bg-red-50 rounded-3xl p-6 shadow-sm border border-red-100 text-center">
        <MapPin className="text-red-400 mx-auto mb-2" size={32} />
        <p className="text-red-700 font-medium mb-3">{locError}</p>
        <button onClick={requestLocation} className="bg-red-100 text-red-800 px-4 py-2 rounded-xl font-bold hover:bg-red-200">
          Enable Location
        </button>
      </div>
    );
  }

  const current = weather?.current;
  const today = weather?.forecast?.[0];
  const rainChance = today ? (today.precipitation_probability_mean || 0) : 0;

  return (
    <div className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-3xl p-6 shadow-sm relative overflow-hidden">
      {/* Location Header */}
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className="flex items-center gap-2 text-agronex-deep">
          <MapPin size={20} className="text-green-600" />
          <div>
            <p className="text-xs font-bold text-green-700 uppercase tracking-wide">Current Location</p>
            <h3 className="font-bold text-lg">{location?.city}, {location?.state}</h3>
          </div>
        </div>
        <button onClick={requestLocation} className="text-green-700 bg-white/50 hover:bg-white/80 p-2 rounded-full transition-colors" title="Refresh Location">
          <Navigation size={16} />
        </button>
      </div>

      {weatherLoading ? (
        <div className="flex items-center gap-2 text-green-700 opacity-60">
          <div className="w-4 h-4 border-2 border-green-700/30 border-t-green-700 rounded-full animate-spin"></div>
          <span className="text-sm font-medium">Fetching live weather...</span>
        </div>
      ) : current ? (
        <div className="relative z-10">
          <div className="flex items-end gap-3 mb-4">
            <span className="text-4xl font-bold text-agronex-deep">{Math.round(current.temperature)}°C</span>
            <span className="text-lg font-medium text-green-800 mb-1">{isTamil && weather.condition_ta ? weather.condition_ta : weather.condition_en}</span>
          </div>
          
          <div className="flex items-center gap-4 text-sm font-semibold text-green-800 mb-5">
            <div className="flex items-center gap-1">
              <CloudRain size={16} className="text-blue-500" />
              Rain chance: {rainChance}%
            </div>
            <div className="flex items-center gap-1">
              <Wind size={16} className="text-orange-500" />
              {current.wind_speed} km/h
            </div>
          </div>

          <Link to="/weather" className="block text-center bg-white text-agronex-deep font-bold py-3 rounded-xl shadow-sm hover:shadow transition-all border border-green-100">
            {isTamil ? "வானிலை விவரங்களைக் காண்க" : "View Weather Details"}
          </Link>
        </div>
      ) : (
        <div className="text-center py-4">
          <p className="text-red-500 font-bold mb-1">
            {isTamil ? "நேரடி வானிலைத் தரவைப் பெற முடியவில்லை." : "Unable to fetch live weather data."}
          </p>
          <p className="text-red-400 text-sm">
            {isTamil ? "தரவு இல்லை" : "Data unavailable"}
          </p>
        </div>
      )}

      {/* Decorative */}
      <CloudSun size={120} className="absolute -bottom-6 -right-6 text-white opacity-40 pointer-events-none" />
    </div>
  );
}
