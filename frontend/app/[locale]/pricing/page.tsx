'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { createCheckout, type ProductSlug } from '../../../lib/billing-client';
import { isAuthenticated } from '../../../lib/auth-client';

type PlanKey = 'free' | 'premium' | 'pro';

interface Plan {
  key: PlanKey;
  price: string;
  slug?: ProductSlug;
  featured?: boolean;
}

// Prices from docs/PLAN.md Phase 6 pricing matrix.
const PLANS: Plan[] = [
  { key: 'free', price: '$0' },
  { key: 'premium', price: '$9.99', slug: 'premium_monthly', featured: true },
  { key: 'pro', price: '$5.99', slug: 'pro_monthly' },
];

const FEATURE_KEYS = ['natal', 'horoscopes', 'forecasts', 'dreams', 'pdf', 'byok'] as const;

// Which features each tier includes (✓ / —).
const MATRIX: Record<PlanKey, Record<(typeof FEATURE_KEYS)[number], boolean>> = {
  free: { natal: true, horoscopes: false, forecasts: false, dreams: true, pdf: false, byok: false },
  premium: { natal: true, horoscopes: true, forecasts: true, dreams: true, pdf: true, byok: false },
  pro: { natal: true, horoscopes: true, forecasts: true, dreams: true, pdf: true, byok: true },
};

export default function PricingPage() {
  const t = useTranslations('Pricing');
  const params = useParams();
  const router = useRouter();
  const locale = (params?.locale as string) || 'ru';

  const [loadingSlug, setLoadingSlug] = useState<ProductSlug | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubscribe(slug?: ProductSlug) {
    setError(null);
    if (!slug) {
      router.push(`/${locale}/astrology`);
      return;
    }
    if (!isAuthenticated()) {
      // Send to account to log in, then come back to pricing.
      router.push(`/${locale}/account?next=pricing`);
      return;
    }
    setLoadingSlug(slug);
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : '';
      const { url } = await createCheckout({
        productSlug: slug,
        successRedirect: `${origin}/${locale}/checkout/success`,
      });
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setLoadingSlug(null);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <header className="mx-auto max-w-2xl text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-gold sm:text-4xl">
          {t('title')}
        </h1>
        <p className="mt-4 text-ink-muted">{t('subtitle')}</p>
      </header>

      {error && (
        <p
          role="alert"
          className="mx-auto mt-6 max-w-2xl rounded-md border border-red-400/40 bg-red-500/10 px-4 py-3 text-center text-sm text-red-300"
        >
          {error}
        </p>
      )}

      <div className="mt-10 grid gap-6 md:grid-cols-3">
        {PLANS.map((plan) => (
          <section
            key={plan.key}
            className={`relative flex flex-col rounded-2xl border p-6 ${
              plan.featured
                ? 'border-gold bg-surfaceStrong shadow-lg'
                : 'border-gold-soft bg-surface'
            }`}
          >
            {plan.featured && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gold px-3 py-1 text-xs font-semibold text-bg">
                {t('mostPopular')}
              </span>
            )}
            <h2 className="text-xl font-semibold text-gold">{t(`plans.${plan.key}.name`)}</h2>
            <p className="mt-2 flex items-baseline gap-1">
              <span className="text-3xl font-bold text-ink">{plan.price}</span>
              {plan.key !== 'free' && (
                <span className="text-sm text-ink-muted">{t('perMonth')}</span>
              )}
            </p>
            <p className="mt-2 min-h-[2.5rem] text-sm text-ink-muted">
              {t(`plans.${plan.key}.tagline`)}
            </p>

            <ul className="mt-6 space-y-2 text-sm">
              {FEATURE_KEYS.map((fk) => {
                const on = MATRIX[plan.key][fk];
                return (
                  <li key={fk} className="flex items-center gap-2">
                    <span className={on ? 'text-gold' : 'text-ink-muted/50'}>
                      {on ? '✓' : '—'}
                    </span>
                    <span className={on ? 'text-ink' : 'text-ink-muted/60 line-through'}>
                      {t(`features.${fk}`)}
                    </span>
                  </li>
                );
              })}
            </ul>

            <button
              type="button"
              onClick={() => handleSubscribe(plan.slug)}
              disabled={loadingSlug !== null}
              className={`mt-6 inline-flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                plan.featured
                  ? 'bg-gold text-bg hover:bg-gold-soft'
                  : 'border border-gold-soft text-gold hover:bg-surfaceStrong'
              }`}
            >
              {loadingSlug === plan.slug
                ? t('redirecting')
                : plan.key === 'free'
                  ? t('cta.free')
                  : t('cta.subscribe')}
            </button>
          </section>
        ))}
      </div>

      {/* One-time products */}
      <section className="mt-12 rounded-2xl border border-gold-soft bg-surface p-6">
        <h2 className="text-lg font-semibold text-gold">{t('oneTime.title')}</h2>
        <p className="mt-1 text-sm text-ink-muted">{t('oneTime.subtitle')}</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <OneTimeCard
            title={t('oneTime.natalPdf.name')}
            desc={t('oneTime.natalPdf.desc')}
            price="$19"
            onBuy={() => handleSubscribe('natal_pdf')}
            busy={loadingSlug === 'natal_pdf'}
            buyLabel={t('cta.buy')}
            busyLabel={t('redirecting')}
          />
          <OneTimeCard
            title={t('oneTime.yearly.name')}
            desc={t('oneTime.yearly.desc')}
            price="$29"
            onBuy={() => handleSubscribe('yearly_forecast')}
            busy={loadingSlug === 'yearly_forecast'}
            buyLabel={t('cta.buy')}
            busyLabel={t('redirecting')}
          />
        </div>
      </section>

      <p className="mt-8 text-center text-xs text-ink-muted">
        {t('disclaimer')}{' '}
        <Link href={`/${locale}/account`} className="text-gold underline hover:no-underline">
          {t('manageLink')}
        </Link>
      </p>
    </main>
  );
}

function OneTimeCard({
  title,
  desc,
  price,
  onBuy,
  busy,
  buyLabel,
  busyLabel,
}: {
  title: string;
  desc: string;
  price: string;
  onBuy: () => void;
  busy: boolean;
  buyLabel: string;
  busyLabel: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-gold-soft bg-surfaceStrong p-4">
      <div>
        <h3 className="font-medium text-ink">{title}</h3>
        <p className="mt-0.5 text-xs text-ink-muted">{desc}</p>
      </div>
      <div className="flex flex-col items-end gap-1">
        <span className="text-lg font-bold text-gold">{price}</span>
        <button
          type="button"
          onClick={onBuy}
          disabled={busy}
          className="rounded-md border border-gold-soft px-3 py-1.5 text-xs font-semibold text-gold transition-colors hover:bg-surface disabled:opacity-60"
        >
          {busy ? busyLabel : buyLabel}
        </button>
      </div>
    </div>
  );
}
