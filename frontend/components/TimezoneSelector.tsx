'use client';

import {useEffect, useState} from 'react';
import {useTranslations} from 'next-intl';

export interface Timezone {
  value: string;
  label: string;
  region: string;
  utc_offset: string;
}

interface Props {
  value: string;
  onChange: (timezone: string) => void;
  className?: string;
}

const STORAGE_KEY = 'oneiroscope_timezone';

export function getStoredTimezone(): string {
  if (typeof window === 'undefined') {
    return 'Europe/Moscow';
  }
  return localStorage.getItem(STORAGE_KEY) || 'Europe/Moscow';
}

export function setStoredTimezone(tz: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, tz);
  }
}

export default function TimezoneSelector({value, onChange, className = ''}: Props) {
  const t = useTranslations('TimezoneSelector');
  const [timezones, setTimezones] = useState<Timezone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTimezones = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/timezones');
        if (!response.ok) {
          throw new Error('Failed to fetch timezones');
        }
        const data = await response.json();
        setTimezones(data.timezones || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        // Fallback to default timezones
        setTimezones([
          {value: 'Europe/Moscow', label: 'Москва (UTC+3)', region: 'Европа', utc_offset: '+03:00'},
          {value: 'Europe/Kiev', label: 'Киев (UTC+2)', region: 'Европа', utc_offset: '+02:00'},
          {value: 'Europe/Prague', label: 'Прага (UTC+1)', region: 'Европа', utc_offset: '+01:00'},
          {value: 'UTC', label: 'UTC', region: 'Общее', utc_offset: '+00:00'},
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchTimezones();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newTz = e.target.value;
    setStoredTimezone(newTz);
    onChange(newTz);
  };

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-sm text-ink-muted">{t('loading')}</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-sm text-red-500">{t('error')}</span>
      </div>
    );
  }

  // Group by region
  const grouped = timezones.reduce((acc, tz) => {
    if (!acc[tz.region]) {
      acc[tz.region] = [];
    }
    acc[tz.region].push(tz);
    return acc;
  }, {} as Record<string, Timezone[]>);

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <label htmlFor="timezone-select" className="text-sm font-medium text-gold">
        <span className="flex items-center gap-2">
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {t('label')}
        </span>
      </label>
      <select
        id="timezone-select"
        value={value}
        onChange={handleChange}
        className="rounded-md border border-gold-soft bg-surfaceStrong px-3 py-2 text-sm text-ink transition-colors duration-200 focus:border-gold focus:outline-none focus:ring-2 focus:ring-gold focus:ring-opacity-50"
      >
        {Object.entries(grouped).map(([region, tzList]) => (
          <optgroup key={region} label={region}>
            {tzList.map((tz) => (
              <option key={tz.value} value={tz.value}>
                {tz.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="text-xs text-ink-muted">{t('description')}</p>
    </div>
  );
}
