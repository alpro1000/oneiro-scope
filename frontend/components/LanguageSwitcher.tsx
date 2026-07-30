'use client';

import {usePathname, useRouter, useParams} from 'next/navigation';

const locales = [
  {code: 'ru', label: 'RU'},
  {code: 'en', label: 'EN'},
  {code: 'de', label: 'DE'},
  {code: 'es', label: 'ES'},
  {code: 'fr', label: 'FR'},
];

export default function LanguageSwitcher() {
  const pathname = usePathname();
  const router = useRouter();
  const params = useParams();
  const current = (params?.locale as string) || 'ru';

  const switchLocale = (next: string) => {
    if (next === current) return;
    // Swap the locale segment, preserving the rest of the path.
    const segments = (pathname || `/${current}`).split('/');
    segments[1] = next;
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferred-locale', next);
    }
    router.push(segments.join('/'));
  };

  return (
    <div style={{display: 'inline-flex', border: '1px solid var(--grat-2)'}}>
      {locales.map((locale, i) => {
        const active = current === locale.code;
        return (
          <button
            key={locale.code}
            type="button"
            onClick={() => switchLocale(locale.code)}
            aria-label={`Switch to ${locale.label}`}
            aria-current={active ? 'true' : undefined}
            style={{
              background: active ? 'var(--brass)' : 'transparent',
              color: active ? 'var(--abyss)' : 'var(--muted)',
              border: 0,
              borderLeft: i > 0 ? '1px solid var(--grat-2)' : 0,
              fontFamily: 'var(--font-data)',
              fontSize: 10.5,
              letterSpacing: '.06em',
              padding: '5px 7px',
              cursor: active ? 'default' : 'pointer',
            }}
          >
            {locale.label}
          </button>
        );
      })}
    </div>
  );
}
