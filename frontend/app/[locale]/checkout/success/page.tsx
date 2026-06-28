'use client';

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
    <main className="mx-auto max-w-md px-4 py-16 text-center sm:px-6">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gold/15 text-3xl text-gold">
        ✓
      </div>
      <h1 className="mt-6 text-2xl font-semibold text-gold">{t('title')}</h1>
      <p className="mt-3 text-ink-muted">
        {checking
          ? t('verifying')
          : activated
            ? t('activated', { tier: t(`tiers.${sub!.tier}`) })
            : t('pending')}
      </p>

      <div className="mt-8 flex flex-col gap-3">
        <Link
          href={`/${locale}/account`}
          className="inline-flex items-center justify-center rounded-lg bg-gold px-4 py-2.5 text-sm font-semibold text-bg transition-colors hover:bg-gold-soft"
        >
          {t('goToAccount')}
        </Link>
        <Link
          href={`/${locale}/astrology`}
          className="inline-flex items-center justify-center rounded-lg border border-gold-soft px-4 py-2.5 text-sm font-semibold text-gold transition-colors hover:bg-surfaceStrong"
        >
          {t('startUsing')}
        </Link>
      </div>
    </main>
  );
}
