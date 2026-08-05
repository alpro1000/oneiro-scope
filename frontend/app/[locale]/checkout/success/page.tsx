'use client';

/**
 * Checkout success — instrument screen.
 *
 * Polling logic unchanged. Presentation moved off the transitional Tailwind
 * bridge onto the tokens, and the "start using" link now points at /natal:
 * /astrology is the superseded screen that was dropped from the nav, so
 * sending a user who just paid to it was a dead end by our own decision.
 */

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getSubscription, type SubscriptionSummary } from '../../../../lib/billing-client';
import { isAuthenticated } from '../../../../lib/auth-client';

export default function CheckoutSuccessPage() {
  const t = useTranslations('CheckoutSuccess');
  const params = useParams();
  const locale = (params?.locale as string) || 'ru';
  const ru = locale === 'ru';

  const [sub, setSub] = useState<SubscriptionSummary | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function poll(attempt = 0) {
      if (!isAuthenticated()) {
        setChecking(false);
        return;
      }
      try {
        const s = await getSubscription();
        if (cancelled) return;
        // Lemon webhook may lag a few seconds — retry while still free.
        if (s.tier === 'free' && attempt < 5) {
          setTimeout(() => poll(attempt + 1), 2000);
          return;
        }
        setSub(s);
        setChecking(false);
      } catch {
        if (cancelled) return;
        setChecking(false);
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  const activated = sub && sub.tier !== 'free';

  return (
    <main style={{ padding: 'clamp(14px,2.2vw,30px)', maxWidth: 520, margin: '0 auto' }}>
      <header style={{ paddingBottom: 14, marginBottom: 18, borderBottom: '1px solid var(--grat-1)' }}>
        <span className="eyebrow">{ru ? 'оплата' : 'checkout'}</span>
        <h1 style={{ fontSize: 'clamp(26px,4.5vw,42px)', margin: '4px 0 0' }}>{t('title')}</h1>
      </header>

      <div style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '15px 16px' }}>
        <p
          className={checking ? 'num' : undefined}
          style={{
            margin: 0,
            fontSize: checking ? 12 : 14,
            lineHeight: 1.6,
            letterSpacing: checking ? '.04em' : undefined,
            color: checking ? 'var(--muted)' : 'var(--parchment)',
          }}
        >
          {checking
            ? t('verifying')
            : activated
              ? t('activated', { tier: t(`tiers.${sub!.tier}`) })
              : t('pending')}
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 9, marginTop: 16 }}>
        <Link
          href={`/${locale}/account`}
          style={{
            textAlign: 'center',
            background: 'var(--brass)',
            color: 'var(--abyss)',
            fontFamily: 'var(--font-ui)',
            fontWeight: 600,
            fontSize: 13,
            padding: '10px 18px',
            letterSpacing: '.02em',
          }}
        >
          {t('goToAccount')}
        </Link>
        <Link
          href={`/${locale}/natal`}
          style={{
            textAlign: 'center',
            border: '1px solid var(--brass-dim)',
            color: 'var(--brass)',
            fontFamily: 'var(--font-ui)',
            fontWeight: 600,
            fontSize: 13,
            padding: '10px 18px',
            letterSpacing: '.02em',
          }}
        >
          {t('startUsing')}
        </Link>
      </div>
    </main>
  );
}
