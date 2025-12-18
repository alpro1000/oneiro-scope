'use client';

import {usePathname, useRouter} from 'next/navigation';
import {useParams} from 'next/navigation';

const locales = [
  {code: 'ru', label: 'RU', flag: ''},
  {code: 'en', label: 'EN', flag: ''},
];

export default function LanguageSwitcher() {
  const pathname = usePathname();
  const router = useRouter();
  const params = useParams();
  const currentLocale = (params?.locale as string) || 'ru';

  const switchLocale = (newLocale: string) => {
    if (newLocale === currentLocale) return;

    // Replace the locale in the pathname
    const segments = pathname.split('/');
    segments[1] = newLocale;
    const newPath = segments.join('/');

    // Store preference in localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferred-locale', newLocale);
    }

    router.push(newPath);
  };

  return (
    <div className="flex items-center gap-1 rounded-md bg-surfaceStrong p-1">
      {locales.map((locale) => (
        <button
          key={locale.code}
          onClick={() => switchLocale(locale.code)}
          className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
            currentLocale === locale.code
              ? 'bg-gold text-bg'
              : 'text-ink-muted hover:text-gold'
          }`}
          aria-label={`Switch to ${locale.label}`}
        >
          {locale.label}
        </button>
      ))}
    </div>
  );
}
