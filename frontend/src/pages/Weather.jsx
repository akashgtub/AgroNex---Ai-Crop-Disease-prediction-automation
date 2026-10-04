import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ChevronLeft, MapPin, Search, CloudRain, Wind, ThermometerSun, AlertTriangle, CloudSun, Droplets, Sunrise, Sunset } from 'lucide-react';
import { useLocation } from '../hooks/useLocation';

export default function Weather() {
  const { t, i18n } = useTranslation();
  const { location, loading: locLoading, error: locError, requestLocation, updateLocationManually } = useLocation();
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const isTamil = i18n.language === 'ta';

  useEffect(() => {
    if (location?.latitude && location?.longitude) {
      fetchWeather(location.latitude, location.longitude);
    }
  }, [location]);

  const fetchWeather = async (lat, lon) => {
    setWeatherLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/weather/forecast?lat=${lat}&lon=${lon}`);
      if (response.ok) {
        setWeather(await response.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setWeatherLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(searchQuery)}&count=1&language=en&format=json`);
      const data = await res.json();
      if (data.results && data.results.length > 0) {
        const place = data.results[0];
        updateLocationManually(place.latitude, place.longitude, place.name, place.admin1, place.country);
        setSearchMode(false);
      } else {
        alert("Location not found");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'rain': return <CloudRain size={24} />;
      case 'thunderstorm': return <AlertTriangle size={24} />;
      case 'wind': return <Wind size={24} />;
      case 'heat': return <ThermometerSun size={24} />;
      case 'humidity': return <Droplets size={24} />;
      default: return <AlertTriangle size={24} />;
    }
  };

  const getAlertColors = (type) => {
    if (type === 'rain') return "bg-blue-50 border-blue-200 text-blue-900";
    if (type === 'wind') return "bg-orange-50 border-orange-200 text-orange-900";
    if (type === 'thunderstorm' || type === 'heat') return "bg-red-50 border-red-200 text-red-900";
    return "bg-green-50 border-green-200 text-green-900";
  };

  return (
    <div className="pb-24 max-w-lg mx-auto">
      {/* Header */}
      <div className="bg-white px-4 py-4 sticky top-0 z-50 shadow-sm flex items-center gap-3">
        <Link to="/dashboard" className="p-2 -ml-2 bg-gray-50 rounded-full text-agronex-deep hover:bg-gray-100 transition-colors">
          <ChevronLeft size={24} />
        </Link>
        <h1 className="text-xl font-black text-agronex-deep flex-grow">
          {isTamil ? "வானிலை விவரங்கள்" : "Weather Details"}
        </h1>
      </div>

      <div className="px-4 mt-6">
        {/* Location Section */}
        <div className="bg-white rounded-3xl p-5 shadow-sm border border-gray-100 mb-6">
          {!searchMode ? (
            <div className="flex justify-between items-center">
              <div className="flex items-start gap-3">
                <MapPin className="text-green-600 mt-1" size={24} />
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wide">Location</p>
                  <h3 className="font-bold text-lg text-agronex-deep">
                    {locLoading ? "Detecting..." : location ? `${location.city}, ${location.state}` : "Unknown"}
                  </h3>
                </div>
              </div>
              <button onClick={() => setSearchMode(true)} className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1.5 rounded-lg">
                Change
              </button>
            </div>
          ) : (
            <form onSubmit={handleSearch} className="flex gap-2">
              <input 
                type="text" 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search city..." 
                className="flex-grow bg-gray-50 border border-gray-200 rounded-xl px-4 py-2 font-medium focus:outline-none focus:ring-2 focus:ring-green-500"
                autoFocus
              />
              <button type="submit" className="bg-green-600 text-white p-2 rounded-xl">
                <Search size={20} />
              </button>
              <button type="button" onClick={() => setSearchMode(false)} className="bg-gray-100 text-gray-600 px-3 rounded-xl font-bold">
                Cancel
              </button>
            </form>
          )}
        </div>

        {weatherLoading ? (
          <div className="text-center py-10 opacity-60">
            <div className="w-8 h-8 border-4 border-green-200 border-t-green-600 rounded-full animate-spin mx-auto mb-3"></div>
            <p className="font-medium text-gray-500">Loading weather data...</p>
          </div>
        ) : weather && weather.current ? (
          <>
            {/* Current Weather Card */}
            <div className="bg-gradient-to-br from-agronex-primary to-green-700 rounded-3xl p-6 text-white shadow-md mb-6 relative overflow-hidden">
              <div className="relative z-10 flex justify-between items-end">
                <div>
                  <p className="text-5xl font-black mb-2">{Math.round(weather.current.temperature)}°</p>
                  <p className="text-lg font-bold opacity-90">{isTamil && weather.condition_ta ? weather.condition_ta : weather.condition_en}</p>
                </div>
                <div className="text-right">
                  <CloudSun size={48} className="mb-2 inline-block opacity-80" />
                  <p className="font-medium opacity-80 text-sm">Feels like {Math.round(weather.current.temperature + 2)}°</p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mt-6 pt-4 border-t border-white/20 relative z-10">
                <div className="flex items-center gap-2">
                  <Droplets size={18} className="opacity-70" />
                  <span className="font-medium">{weather.current.humidity}% Humidity</span>
                </div>
                <div className="flex items-center gap-2">
                  <Wind size={18} className="opacity-70" />
                  <span className="font-medium">{weather.current.wind_speed} km/h Wind</span>
                </div>
              </div>
              
              <CloudSun size={180} className="absolute -bottom-10 -right-10 opacity-10 pointer-events-none" />
            </div>

            {/* Agricultural Weather Alerts */}
            <h3 className="font-black text-lg text-agronex-deep mb-3 flex items-center gap-2">
              <AlertTriangle size={20} className="text-orange-500" />
              {isTamil ? "வேளாண் எச்சரிக்கைகள்" : "Agricultural Alerts"}
            </h3>
            
            <div className="space-y-3 mb-8">
              {weather.alerts && weather.alerts.length > 0 ? (
                weather.alerts.map((alert, idx) => (
                  <div key={idx} className={`p-4 rounded-2xl border ${getAlertColors(alert.type)} flex items-start gap-4 shadow-sm`}>
                    <div className="mt-1 opacity-80">{getAlertIcon(alert.type)}</div>
                    <div>
                      <h4 className="font-bold text-lg mb-1">{isTamil ? alert.title_ta : alert.title_en}</h4>
                      <p className="text-sm font-medium opacity-90 leading-relaxed mb-2">
                        {isTamil ? alert.message_ta : alert.message_en}
                      </p>
                      {alert.probability && (
                        <span className="inline-block bg-white/40 px-2 py-1 rounded text-xs font-bold">
                          {alert.probability}% Probability
                        </span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="bg-green-50 p-4 rounded-2xl border border-green-100 flex items-center gap-3">
                  <div className="bg-white p-2 rounded-full text-green-500">
                    <CloudSun size={20} />
                  </div>
                  <div>
                    <h4 className="font-bold text-green-800">No Significant Alerts</h4>
                    <p className="text-sm text-green-600 font-medium">Weather is optimal for farming.</p>
                  </div>
                </div>
              )}
            </div>

            {/* 7 Day Forecast */}
            <h3 className="font-black text-lg text-agronex-deep mb-3">
              {isTamil ? "அடுத்த 7 நாட்கள்" : "7-Day Forecast"}
            </h3>
            <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden mb-6">
              {weather.forecast?.map((day, idx) => {
                const dateObj = new Date(day.date);
                const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                return (
                  <div key={idx} className="flex items-center justify-between p-4 border-b border-gray-50 last:border-0">
                    <span className="w-16 font-bold text-gray-700">{idx === 0 ? 'Today' : dayName}</span>
                    <div className="flex-grow flex items-center justify-center gap-2 text-blue-500 font-medium text-sm">
                      <CloudRain size={16} />
                      {day.precipitation_probability_mean}%
                    </div>
                    <div className="w-24 text-right font-bold text-gray-800">
                      {Math.round(day.temperature_max)}° <span className="opacity-40 text-sm font-medium">{Math.round(day.temperature_min)}°</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
