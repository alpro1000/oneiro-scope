'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  login,
  register,
  fetchMe,
  logout,
  isAuthenticated,
  type UserMe,
} from '../../../lib/auth-client';
import { getSubscription, type SubscriptionSummary } from '../../../lib/billing-client';

type Mode = 'login' | 'register';

export default function AccountPage() {
  const t = useTranslations('Account');
  const params = useParams();
  const router = useRouter();
  const search = useSearchParams();
  const locale = (params?.locale as string) || 'ru';

  const [authed, setAuthed] = useState(false);
  const [checking, setChecking] = useState(true);
  const [me, setMe] = useState<UserMe | null>(null);
  const [sub, setSub] = useState<SubscriptionSummary | null>(null);

  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadProfile() {
    try {
      const [user, subscription] = await Promise.all([
        fetchMe(),
        getSubscription().catch(() => null),
      ]);
      setMe(user);
      setSub(subscription);
      setAuthed(true);
    } catch {
      // Token invalid/expired — fall back to the auth form.
      logout();
      setAuthed(false);
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    if (isAuthenticated()) {
      loadProfile();
    } else {
      setChecking(false);
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === 'register') {
        await register({ email, password, name: name || undefined, language: locale });
      } else {
        await login({ email, password });
      }
      await loadProfile();
      // If the user came from pricing, send them back to complete checkout.
      if (search?.get('next') === 'pricing') {
        router.push(`/${locale}/pricing`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function handleLogout() {
    logout();
    setAuthed(false);
    setMe(null);
    setSub(null);
  }

  if (checking) {
    return (
      <main className="mx-auto max-w-md px-4 py-16 text-center text-inkMuted">
        {t('loading')}
      </main>
    );
  }

  // ----- Authenticated view: profile + subscription -----
  if (authed && me) {
    const tier = sub?.tier || me.tier || 'free';
    return (
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <h1 className="text-2xl font-semibold text-gold">{t('title')}</h1>

        <section className="mt-6 rounded-2xl border border-goldSoft bg-surface p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-inkMuted">
            {t('profile')}
          </h2>
          <dl className="mt-3 space-y-2 text-sm">
            <Row label={t('email')} value={me.email || '—'} />
            {me.name && <Row label={t('name')} value={me.name} />}
            <Row label={t('language')} value={me.language.toUpperCase()} />
          </dl>
        </section>

        <section className="mt-6 rounded-2xl border border-goldSoft bg-surface p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-inkMuted">
            {t('subscription')}
          </h2>
          <div className="mt-3 flex items-center gap-3">
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                tier === 'free'
                  ? 'bg-surfaceStrong text-inkMuted'
                  : 'bg-gold text-bg'
              }`}
            >
              {t(`tiers.${tier}`)}
            </span>
            {sub?.status && (
              <span className="text-xs text-inkMuted">
                {t('status')}: {sub.status}
              </span>
            )}
          </div>
          {sub?.current_period_end && (
            <p className="mt-2 text-xs text-inkMuted">
              {sub.cancel_at_period_end ? t('endsOn') : t('renewsOn')}:{' '}
              {new Date(sub.current_period_end).toLocaleDateString(locale)}
            </p>
          )}
          {tier === 'free' && (
            <Link
              href={`/${locale}/pricing`}
              className="mt-4 inline-flex rounded-lg bg-gold px-4 py-2 text-sm font-semibold text-bg transition-colors hover:bg-goldSoft"
            >
              {t('upgrade')}
            </Link>
          )}
        </section>

        <button
          type="button"
          onClick={handleLogout}
          className="mt-6 text-sm text-inkMuted underline transition-colors hover:text-gold"
        >
          {t('logout')}
        </button>
      </main>
    );
  }

  // ----- Unauthenticated view: login / register form -----
  return (
    <main className="mx-auto max-w-md px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-semibold text-gold">
        {mode === 'login' ? t('loginTitle') : t('registerTitle')}
      </h1>
      <p className="mt-2 text-sm text-inkMuted">
        {mode === 'login' ? t('loginSubtitle') : t('registerSubtitle')}
      </p>

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-md border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-300"
        >
          {error}
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {mode === 'register' && (
          <Field
            label={t('name')}
            type="text"
            value={name}
            onChange={setName}
            autoComplete="name"
            required={false}
          />
        )}
        <Field
          label={t('email')}
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          required
        />
        <Field
          label={t('password')}
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          required
          hint={mode === 'register' ? t('passwordHint') : undefined}
        />

        <button
          type="submit"
          disabled={busy}
          className="inline-flex w-full items-center justify-center rounded-lg bg-gold px-4 py-2.5 text-sm font-semibold text-bg transition-colors hover:bg-goldSoft disabled:opacity-60"
        >
          {busy
            ? t('submitting')
            : mode === 'login'
              ? t('loginCta')
              : t('registerCta')}
        </button>
      </form>

      <button
        type="button"
        onClick={() => {
          setMode(mode === 'login' ? 'register' : 'login');
          setError(null);
        }}
        className="mt-4 text-sm text-inkMuted transition-colors hover:text-gold"
      >
        {mode === 'login' ? t('switchToRegister') : t('switchToLogin')}
      </button>
    </main>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-inkMuted">{label}</dt>
      <dd className="text-ink">{value}</dd>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
  required,
  hint,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-ink">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required={required}
        className="mt-1 w-full rounded-lg border border-goldSoft bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-gold focus-visible:ring-2 focus-visible:ring-gold"
      />
      {hint && <span className="mt-1 block text-xs text-inkMuted">{hint}</span>}
    </label>
  );
}
