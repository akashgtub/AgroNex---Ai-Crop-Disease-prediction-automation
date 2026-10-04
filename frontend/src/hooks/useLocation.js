import { useState, useEffect } from 'react';

export function useLocation() {
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const savedLocation = localStorage.getItem('agronex_location');
    if (savedLocation) {
      setLocation(JSON.parse(savedLocation));
      setLoading(false);
    } else {
      requestLocation();
    }
  }, []);

  const requestLocation = () => {
    setLoading(true);
    setError(null);
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser");
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const res = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`);
          const data = await res.json();
          const newLoc = {
            latitude,
            longitude,
            city: data.city || data.locality || "Unknown City",
            state: data.principalSubdivision || "",
            country: data.countryName || ""
          };
          setLocation(newLoc);
          localStorage.setItem('agronex_location', JSON.stringify(newLoc));
          setLoading(false);
        } catch (err) {
          setError("Failed to determine city name.");
          setLoading(false);
        }
      },
      (err) => {
        setError("Location access denied. Please enable location or choose manually.");
        setLoading(false);
      },
      { timeout: 10000 }
    );
  };

  const updateLocationManually = (lat, lon, city, state, country) => {
    const newLoc = { latitude: lat, longitude: lon, city, state, country };
    setLocation(newLoc);
    localStorage.setItem('agronex_location', JSON.stringify(newLoc));
  };

  return { location, loading, error, requestLocation, updateLocationManually };
}
