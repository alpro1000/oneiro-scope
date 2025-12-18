'use client';

import Link from 'next/link';
import {useParams} from 'next/navigation';
import {useTranslations} from 'next-intl';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const params = useParams();
  const locale = params?.locale as string || 'ru';
  const t = useTranslations('Header');

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gold-soft bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link
          href={`/${locale}`}
          className="flex items-center gap-3 transition-opacity hover:opacity-80"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-gold to-gold-soft shadow-md">
            <svg
              viewBox="0 0 100 100"
              className="h-6 w-6"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M 60 30 A 18 18 0 1 1 60 70 A 13 13 0 1 0 60 30 Z"
                fill="currentColor"
                className="text-bg"
              />
              <circle cx="40" cy="40" r="1.5" fill="currentColor" className="text-bg" opacity="0.7"/>
              <circle cx="35" cy="55" r="1" fill="currentColor" className="text-bg" opacity="0.5"/>
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-semibold tracking-tight text-gold">
              OneiroScope
            </span>
            <span className="text-xs text-ink-muted tracking-wide">
              {t('tagline')}
            </span>
          </div>
        </Link>

        {/* Navigation + Language Switcher */}
        <div className="flex items-center gap-4">
          <nav className="flex items-center gap-1 sm:gap-2">
            <NavLink href={`/${locale}`} label={t('home')} />
            <NavLink href={`/${locale}/calendar`} label={t('calendar')} />
            <NavLink href={`/${locale}/astrology`} label={t('astrology')} />
            <NavLink href={`/${locale}/dreams`} label={t('dreams')} />
          </nav>
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}

function NavLink({href, label}: {href: string; label: string}) {
  return (
    <Link
      href={href}
      className="rounded-md px-3 py-2 text-sm font-medium text-ink transition-colors hover:bg-surfaceStrong hover:text-gold focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
    >
      {label}
    </Link>
  );
}
