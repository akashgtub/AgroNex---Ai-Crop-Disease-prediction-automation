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
  const rainChance = today ? Math.max(...weather.forecast.map(d => d.precipitation_probability_mean || 0)) : 0;

  return (
    <div className="relative rounded-3xl p-6 shadow-sm border border-emerald-100 bg-gradient-to-br from-emerald-50/90 via-teal-50/50 to-green-50/80 overflow-hidden">
      {/* Location Header */}
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
            <MapPin size={17} />
          </div>
          <div>
            <p className="text-[10px] font-extrabold text-emerald-800 uppercase tracking-wider">
              {isTamil ? "தற்போதைய பண்ணை இருப்பிடம்" : "CURRENT FARM LOCATION"}
            </p>
            <h3 className="font-bold text-base text-agronex-deep">
              {location?.city ? `${location.city}, ${location.state}` : (isTamil ? "இருப்பிடம் பெறப்படுகிறது..." : "Detecting location...")}
            </h3>
          </div>
        </div>
        <button 
          onClick={requestLocation} 
          className="text-emerald-700 bg-white/80 hover:bg-white p-2 rounded-xl border border-emerald-200/50 shadow-xs hover:scale-105 active:scale-95 transition-all" 
          title="Refresh Location"
        >
          <Navigation size={15} />
        </button>
      </div>

      {weatherLoading ? (
        <div className="flex items-center gap-2 text-emerald-800 py-4">
          <div className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-semibold">{isTamil ? "நேரலை வானிலை பெறப்படுகிறது..." : "Fetching live weather..."}</span>
        </div>
      ) : current ? (
        <div className="relative z-10">
          <div className="flex items-baseline justify-between mb-4">
            <div className="flex items-baseline gap-2">
              <span className="text-4xl sm:text-5xl font-extrabold text-agronex-deep font-display tracking-tight">
                {Math.round(current.temperature)}°
              </span>
              <span className="text-sm font-bold text-gray-400">C</span>
            </div>
            <div className="text-right">
              <span className="text-base font-bold text-emerald-950 block">
                {isTamil && weather.condition_ta ? weather.condition_ta : weather.condition_en}
              </span>
              <span className="text-xs text-emerald-700 font-medium">
                {isTamil ? "இன்றைய நிலவரம்" : "Today's forecast"}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-2.5 mb-4">
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-xs p-2.5 rounded-xl border border-emerald-100/60 text-xs font-semibold text-gray-700">
              <CloudRain size={16} className="text-blue-500 flex-shrink-0" />
              <span>{isTamil ? "மழை வாய்ப்பு" : "Rain"}: <strong className="text-blue-900">{rainChance}%</strong></span>
            </div>
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-xs p-2.5 rounded-xl border border-emerald-100/60 text-xs font-semibold text-gray-700">
              <Wind size={16} className="text-teal-600 flex-shrink-0" />
              <span>{isTamil ? "காற்று" : "Wind"}: <strong className="text-teal-900">{current.wind_speed} km/h</strong></span>
            </div>
          </div>

          <Link 
            to="/weather" 
            className="flex items-center justify-center gap-2 bg-white hover:bg-emerald-50/80 text-agronex-deep font-bold py-3 rounded-xl shadow-xs border border-emerald-200/80 hover:shadow transition-all text-xs"
          >
            <span>{isTamil ? "முழு வானிலை & மழை முன்னறிவிப்பு" : "View 7-Day Forecast & Alerts"}</span>
            <CloudSun size={15} className="text-emerald-600" />
          </Link>
        </div>
      ) : (
        <p className="text-red-500 text-sm font-medium py-2">Weather data temporarily unavailable</p>
      )}

      {/* Decorative background sun icon */}
      <CloudSun size={140} className="absolute -bottom-8 -right-6 text-emerald-600/10 pointer-events-none" />
    </div>
  );
}
