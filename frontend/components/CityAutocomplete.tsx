'use client';

import {useState, useEffect, useRef} from 'react';
import {motion, AnimatePresence} from 'framer-motion';

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
 * City autocomplete with GeoNames API integration.
 * Shows clear indication when city is found/not found.
 * Prevents submission until valid city is selected.
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

  // Fetch cities from GeoNames API
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
        // Use GeoNames search API
        const username = process.env.NEXT_PUBLIC_GEONAMES_USERNAME || 'demo';
        const url = `https://secure.geonames.org/searchJSON?q=${encodeURIComponent(
          value
        )}&maxRows=10&username=${username}&featureClass=P&orderby=population&lang=${locale}`;

        const response = await fetch(url, {
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error('GeoNames API error');
        }

        const data = await response.json();
        const cities: City[] = (data.geonames || []).map((geo: any) => ({
          name: geo.name,
          country: geo.countryName,
          adminName: geo.adminName1 || '',
          lat: geo.lat,
          lon: geo.lng,
          display: `${geo.name}, ${geo.adminName1 ? geo.adminName1 + ', ' : ''}${geo.countryName}`,
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

  return (
    <div className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => value.length >= 2 && suggestions.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className={`
            w-full p-3 pr-10 bg-slate-900/50 border rounded-lg text-white placeholder-slate-500
            focus:outline-none focus:ring-2 transition-all
            ${selectedCity
              ? 'border-green-500 focus:ring-green-500'
              : showError
                ? 'border-red-500 focus:ring-red-500'
                : 'border-slate-700 focus:ring-amber-500'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />

        {/* Status indicator */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {isLoading && (
            <motion.div
              className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full"
              animate={{rotate: 360}}
              transition={{duration: 1, repeat: Infinity, ease: 'linear'}}
            />
          )}
          {!isLoading && selectedCity && (
            <motion.div
              initial={{scale: 0}}
              animate={{scale: 1}}
              className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center"
            >
              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </motion.div>
          )}
          {!isLoading && !selectedCity && showError && (
            <motion.div
              initial={{scale: 0}}
              animate={{scale: 1}}
              className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center"
            >
              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </motion.div>
          )}
        </div>
      </div>

      {/* Helper text */}
      {selectedCity && (
        <p className="text-xs text-green-400 mt-1 flex items-center gap-1">
          <span>✓</span>
          {locale === 'ru' ? 'Город найден' : 'City found'}
        </p>
      )}
      {!selectedCity && showError && value.length > 2 && (
        <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
          <span>✗</span>
          {locale === 'ru' ? 'Город не найден. Попробуйте другое название.' : 'City not found. Try another name.'}
        </p>
      )}

      {/* Suggestions dropdown */}
      <AnimatePresence>
        {isOpen && suggestions.length > 0 && (
          <motion.div
            ref={dropdownRef}
            initial={{opacity: 0, y: -10}}
            animate={{opacity: 1, y: 0}}
            exit={{opacity: 0, y: -10}}
            className="absolute z-10 w-full mt-2 bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto"
          >
            {suggestions.map((city, index) => (
              <button
                key={`${city.name}-${city.country}-${index}`}
                type="button"
                onClick={() => handleSelect(city)}
                className="w-full px-4 py-3 text-left hover:bg-slate-700 transition-colors flex flex-col gap-1 border-b border-slate-700 last:border-b-0"
              >
                <span className="text-white font-medium">{city.name}</span>
                <span className="text-xs text-slate-400">
                  {city.adminName && `${city.adminName}, `}{city.country}
                </span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
