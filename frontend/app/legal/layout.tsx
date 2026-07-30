import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';

import '../../styles/tokens.css';

export const metadata: Metadata = {
  title: { default: 'Правовые документы · OneiroScope', template: '%s · OneiroScope' },
  robots: { index: true, follow: true },
};

/**
 * Root layout for the /legal branch.
 *
 * These pages sit OUTSIDE `[locale]` on purpose: a privacy policy, terms and
 * disclaimer must live at one fixed URL that opens for anyone — no locale
 * prefix, no auth, no redirect (middleware excludes /legal). Because the app's
 * root layout (`app/layout.tsx`) is a pass-through with no <html>/<body>, this
 * branch supplies its own, exactly as `[locale]/layout.tsx` does. Content is
 * intentionally skeletal for now; the owner supplies the text.
 */
export default function LegalLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body style={{ background: 'var(--abyss)', color: 'var(--parchment)', fontFamily: 'var(--font-ui)' }}>
        <div style={{ maxWidth: '72ch', margin: '0 auto', padding: 'clamp(18px,4vw,56px) clamp(16px,4vw,28px)' }}>
          <header style={{
            display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
            gap: 16, paddingBottom: 16, marginBottom: 'clamp(20px,4vw,40px)',
            borderBottom: '1px solid var(--grat-1)',
          }}>
            <Link href="/" style={{
              fontFamily: 'var(--font-display)', fontSize: 20, letterSpacing: '-.015em',
              color: 'var(--parchment)', textDecoration: 'none',
            }}>
              Oneiro<em style={{ color: 'var(--brass)' }}>Scope</em>
            </Link>
            <span className="eyebrow">правовые документы · legal</span>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
