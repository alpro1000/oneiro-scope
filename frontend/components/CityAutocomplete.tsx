'use client';

import {useState, useEffect, useRef} from 'react';

type City = {
  name: string;
  country: string;
  adminName: string;
  lat: number;
  lon: number;
  display: string;
};

type Props = {
  value: string;
  onChange: (value: string) => void;
  onCitySelect?: (city: City) => void;
  placeholder?: string;
  locale?: string;
  disabled?: boolean;
};

/**
 * City autocomplete with GeoNames API integration — instrument styling.
 *
 * The search logic is unchanged. The presentation was rebuilt: it used green
 * for "found" and red for "not found", i.e. a second and third accent, which
 * the design system forbids — brass carries "resolved", the notice palette
 * carries "not resolved". Each suggestion now also shows its COORDINATES in
 * mono: two cities can share a name (Запорожье the city vs the villages), and
 * the coordinate is the thing that actually distinguishes them — the geocoder
 * ambiguity warning exists for exactly this case.
 */
export default function CityAutocomplete({
  value,
  onChange,
  onCitySelect,
  placeholder = 'Moscow, Russia',
  locale = 'ru',
  disabled = false,
}: Props) {
  const [suggestions, setSuggestions] = useState<City[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [showError, setShowError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch cities from backend API
  useEffect(() => {
    const searchCities = async () => {
      if (!value || value.length < 2) {
        setSuggestions([]);
        setIsOpen(false);
        return;
      }

      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();
      setIsLoading(true);
      setShowError(false);

      try {
        // Use backend API endpoint for city search
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/v1/astrology/cities/search?query=${encodeURIComponent(
          value
        )}&locale=${locale}&max_results=10`;

        const response = await fetch(url, {
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error('City search API error');
        }

        const data = await response.json();
        const cities: City[] = (data.cities || []).map((city: any) => ({
          name: city.name,
          country: city.country,
          adminName: city.admin_name || '',
          lat: city.lat,
          lon: city.lon,
          display: city.display,
        }));

        setSuggestions(cities);
        setIsOpen(cities.length > 0);
        setShowError(cities.length === 0 && value.length > 2);
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Failed to fetch cities:', error);
          setSuggestions([]);
          setShowError(true);
        }
      } finally {
        setIsLoading(false);
      }
    };

    const debounceTimer = setTimeout(searchCities, 300);
    return () => clearTimeout(debounceTimer);
  }, [value, locale]);

  const handleSelect = (city: City) => {
    setSelectedCity(city);
    onChange(city.display);
    setIsOpen(false);
    setShowError(false);
    onCitySelect?.(city);
  };

  const handleInputChange = (newValue: string) => {
    onChange(newValue);
    setSelectedCity(null); // Reset selection when user types
  };

  const borderColor = selectedCity
    ? 'var(--brass)'
    : showError
    ? 'var(--brass-dim)'
    : 'var(--grat-2)';

  return (
    <div style={{position: 'relative'}}>
      <div style={{position: 'relative'}}>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => value.length >= 2 && suggestions.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          style={{
            width: '100%',
            background: 'var(--abyss)',
            color: 'var(--parchment)',
            border: `1px solid ${borderColor}`,
            fontFamily: 'var(--font-ui)',
            fontSize: 13.5,
            padding: '8px 34px 8px 10px',
            opacity: disabled ? 0.5 : 1,
            cursor: disabled ? 'not-allowed' : 'text',
          }}
        />

        {/* Status mark — mono glyph, no coloured pill. */}
        <span
          className="num"
          aria-hidden="true"
          style={{
            position: 'absolute',
            right: 10,
            top: '50%',
            transform: 'translateY(-50%)',
            fontSize: 12,
            color: showError && !selectedCity ? 'var(--notice-ink)' : 'var(--brass)',
          }}
        >
          {isLoading ? '…' : selectedCity ? '✓' : showError ? '✕' : ''}
        </span>
      </div>

      {/* Helper line */}
      {selectedCity && (
        <p
          className="num"
          style={{margin: '4px 0 0', fontSize: 10.5, color: 'var(--dim)', letterSpacing: '.04em'}}
        >
          {locale === 'ru' ? 'город найден' : 'city found'} ·{' '}
          {selectedCity.lat.toFixed(4)}°, {selectedCity.lon.toFixed(4)}°
        </p>
      )}
      {!selectedCity && showError && value.length > 2 && (
        <p
          style={{margin: '4px 0 0', fontSize: 11.5, lineHeight: 1.45, color: 'var(--notice-ink)'}}
        >
          {locale === 'ru'
            ? 'Город не найден. Попробуйте другое написание или укажите страну.'
            : 'City not found. Try another spelling, or add the country.'}
        </p>
      )}

      {/* Suggestions — a panel, 1px dividers, coordinates in mono. */}
      {isOpen && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          style={{
            position: 'absolute',
            zIndex: 10,
            width: '100%',
            marginTop: 4,
            background: 'var(--panel)',
            border: '1px solid var(--grat-2)',
            maxHeight: 260,
            overflowY: 'auto',
          }}
        >
          {suggestions.map((city, index) => (
            <button
              key={`${city.name}-${city.country}-${index}`}
              type="button"
              onClick={() => handleSelect(city)}
              className="city-option"
              style={{
                width: '100%',
                textAlign: 'left',
                background: 'transparent',
                border: 0,
                borderBottom:
                  index < suggestions.length - 1 ? '1px solid var(--grat-1)' : 0,
                padding: '8px 11px',
                cursor: 'pointer',
                display: 'block',
              }}
            >
              <span
                style={{
                  display: 'block',
                  color: 'var(--parchment)',
                  fontFamily: 'var(--font-ui)',
                  fontSize: 13.5,
                }}
              >
                {city.name}
              </span>
              <span
                className="num"
                style={{
                  display: 'block',
                  color: 'var(--dim)',
                  fontSize: 10.5,
                  letterSpacing: '.03em',
                  marginTop: 2,
                }}
              >
                {city.adminName && `${city.adminName}, `}
                {city.country} · {city.lat.toFixed(4)}°, {city.lon.toFixed(4)}°
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
