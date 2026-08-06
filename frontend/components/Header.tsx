'use client';

import Link from 'next/link';
import {useParams, usePathname} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {useState} from 'react';
import LanguageSwitcher from './LanguageSwitcher';

/**
 * Global instrument chrome. The frame is the design system — abyss ground,
 * a single brass accent, parchment ink, 1px graticule borders, no rounding
 * or shadow (killed globally in tokens.css). It sits on top of every screen,
 * so it is styled with the named tokens directly, never the Tailwind palette.
 *
 * The nav leads with the three finished instrument screens (natal,
 * astrocartography, lunar calendar) and keeps the real features still on the
 * old design (dreams, face, account) reachable. The old `/astrology`
 * (superseded by `/natal`) and `/pricing` (payment path is blocked upstream)
 * are intentionally not in the primary nav until they are rebuilt — they still
 * resolve at their URLs. `/face` is back in the nav now that its scanner loads
 * (its runtime is self-hosted); its instrument redesign and analysis fixes are
 * separate follow-ups.
 */
export default function Header() {
  const params = useParams();
  const pathname = usePathname() || '';
  const locale = (params?.locale as string) || 'ru';
  const t = useTranslations('Header');
  const [open, setOpen] = useState(false);

  const links = [
    {href: `/${locale}`, label: t('home'), exact: true},
    {href: `/${locale}/natal`, label: t('natal')},
    {href: `/${locale}/astrocartography`, label: t('astrocartography')},
    {href: `/${locale}/calendar`, label: t('calendar')},
    {href: `/${locale}/dreams`, label: t('dreams')},
    {href: `/${locale}/face`, label: t('face')},
    {href: `/${locale}/connect`, label: t('connect')},
    {href: `/${locale}/account`, label: t('account')},
  ];

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header
      className="sticky top-0 z-50 w-full"
      style={{background: 'var(--abyss)', borderBottom: '1px solid var(--grat-2)'}}
    >
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* wordmark */}
        <Link href={`/${locale}`} className="flex items-baseline gap-2" aria-label="OneiroScope">
          <span aria-hidden style={{color: 'var(--brass)', fontSize: 17}}>☽</span>
          <span className="display" style={{fontSize: 19, color: 'var(--parchment)', letterSpacing: '.01em'}}>
            Oneiro<em style={{fontStyle: 'italic', color: 'var(--brass)'}}>Scope</em>
          </span>
          <span className="eyebrow hidden md:inline" style={{marginLeft: 10}}>{t('tagline')}</span>
        </Link>

        {/* desktop nav */}
        <nav className="hidden lg:flex items-center" style={{gap: 2}}>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="nav-link"
              aria-current={isActive(l.href, l.exact) ? 'page' : undefined}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="hidden lg:flex items-center">
          <LanguageSwitcher />
        </div>

        {/* mobile controls — just the hamburger; the language switcher lives
            inside the open menu so the top row never overflows a 320px screen. */}
        <div className="flex lg:hidden items-center">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={open ? 'Close menu' : 'Open menu'}
            style={{
              background: 'transparent',
              border: '1px solid var(--grat-2)',
              color: 'var(--brass)',
              width: 34,
              height: 34,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontFamily: 'var(--font-data)',
              fontSize: 17,
              lineHeight: 1,
            }}
          >
            {open ? '✕' : '≡'}
          </button>
        </div>
      </div>

      {/* mobile menu */}
      {open && (
        <nav className="lg:hidden" style={{borderTop: '1px solid var(--grat-1)', background: 'var(--shelf)'}}>
          <div className="flex flex-col px-4 py-1">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="nav-link-m"
                aria-current={isActive(l.href, l.exact) ? 'page' : undefined}
              >
                {l.label}
              </Link>
            ))}
            <div style={{padding: '12px 6px 4px'}}>
              <LanguageSwitcher />
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}
