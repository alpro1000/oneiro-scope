'use client';

import {useEffect, useState} from 'react';
import {useTranslations} from 'next-intl';

const STORAGE_KEY = 'oneiro-theme';

export default function ThemeToggle() {
  const t = useTranslations('Header');
  // Matches whatever ThemeInit already set on <html> before hydration —
  // avoids a mismatch flash by reading the DOM, not localStorage again.
  const [theme, setTheme] = useState<'dark' | 'light' | null>(null);

  useEffect(() => {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'light' ? 'light' : 'dark');
  }, []);

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(STORAGE_KEY, next);
    setTheme(next);
  };

  const label = theme === 'dark' ? t('themeLight') : t('themeDark');

  if (theme === null) {
    // Server-rendered placeholder, same footprint as the icon-only
    // mobile button, no flash of empty space.
    return <span className="inline-flex h-9 w-9 sm:w-[9.5rem]" aria-hidden="true" />;
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === 'light'}
      aria-label={label}
      title={label}
      // Icon-only on mobile — a full label + the 5-locale switcher +
      // hamburger overflow the viewport otherwise; label returns at sm+.
      className="inline-flex items-center justify-center gap-2 rounded-full border border-goldSoft bg-surfaceStrong p-2 text-sm text-ink transition-colors hover:border-gold focus:outline-none focus-visible:ring-2 focus-visible:ring-gold sm:justify-start sm:px-3.5 sm:py-2"
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
        {theme === 'dark' ? (
          <path
            d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"
            stroke="currentColor"
            strokeWidth={1.5}
            strokeLinejoin="round"
          />
        ) : (
          <>
            <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth={1.5} />
            <path
              d="M12 2.5v2.2M12 19.3v2.2M21.5 12h-2.2M4.7 12H2.5M18.4 5.6l-1.5 1.5M7.1 16.9l-1.5 1.5M18.4 18.4l-1.5-1.5M7.1 7.1 5.6 5.6"
              stroke="currentColor"
              strokeWidth={1.5}
              strokeLinecap="round"
            />
          </>
        )}
      </svg>
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
