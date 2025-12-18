'use client';

import Link from 'next/link';
import {useParams} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {useState} from 'react';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const params = useParams();
  const locale = params?.locale as string || 'ru';
  const t = useTranslations('Header');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    {href: `/${locale}`, label: t('home')},
    {href: `/${locale}/calendar`, label: t('calendar')},
    {href: `/${locale}/astrology`, label: t('astrology')},
    {href: `/${locale}/dreams`, label: t('dreams')},
  ];

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
          <div className="hidden sm:flex flex-col">
            <span className="text-lg font-semibold tracking-tight text-gold">
              OneiroScope
            </span>
            <span className="text-xs text-ink-muted tracking-wide">
              {t('tagline')}
            </span>
          </div>
        </Link>

        {/* Desktop Navigation + Language Switcher */}
        <div className="hidden md:flex items-center gap-4">
          <nav className="flex items-center gap-2">
            {navLinks.map((link) => (
              <NavLink key={link.href} href={link.href} label={link.label} />
            ))}
          </nav>
          <LanguageSwitcher />
        </div>

        {/* Mobile: Language Switcher + Hamburger */}
        <div className="flex md:hidden items-center gap-2">
          <LanguageSwitcher />
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="inline-flex items-center justify-center rounded-md p-2 text-gold hover:bg-surfaceStrong focus:outline-none focus-visible:ring-2 focus-visible:ring-gold"
            aria-expanded={mobileMenuOpen}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? (
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <nav className="md:hidden border-t border-gold-soft bg-surface/95 backdrop-blur">
          <div className="flex flex-col px-4 py-2 space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-md px-3 py-2 text-sm font-medium text-ink transition-colors hover:bg-surfaceStrong hover:text-gold"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </nav>
      )}
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
