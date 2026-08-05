'use client';

/**
 * Account — instrument screen.
 *
 * Logic (auth, profile, subscription) is unchanged; only the presentation was
 * rebuilt. It was the last screen still reaching the palette through the
 * transitional Tailwind bridge (bg-surface / text-gold / rounded-2xl), so it
 * rendered in roughly the right colours but in the old shape — pills, rounded
 * cards, no eyebrow, no mono. Now it matches natal/calendar/dreams: bordered
 * panels with mono eyebrow labels, brass as the only accent, radius 0, and the
 * refusal palette (--notice-*) for errors instead of a second red accent.
 */

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
  const ru = locale === 'ru';

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
      <main style={{ ...pageStyle, maxWidth: 520 }}>
        <p className="num" style={{ color: 'var(--muted)', fontSize: 12, letterSpacing: '.04em' }}>
          {t('loading')}
        </p>
      </main>
    );
  }

  // ----- Authenticated view: profile + subscription -----
  if (authed && me) {
    const tier = sub?.tier || me.tier || 'free';
    const free = tier === 'free';
    return (
      <main style={{ ...pageStyle, maxWidth: 760 }}>
        <header style={headerStyle}>
          <span className="eyebrow">{ru ? 'кабинет' : 'account'}</span>
          <h1 style={{ fontSize: 'clamp(28px,5vw,52px)', margin: '4px 0 0' }}>{t('title')}</h1>
        </header>

        <div className="panel">
          <div className="panel-block">
            <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>
              {t('profile')}
            </span>
            <table
              className="num"
              style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: 12.5 }}
            >
              <tbody>
                <Row label={t('email')} value={me.email || '—'} />
                {me.name && <Row label={t('name')} value={me.name} />}
                <Row label={t('language')} value={me.language.toUpperCase()} />
              </tbody>
            </table>
          </div>

          <div className="panel-block">
            <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>
              {t('subscription')}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              {/* Tier reads as a stamped label, not a coloured pill. */}
              <span
                className="num"
                style={{
                  border: `1px solid ${free ? 'var(--grat-2)' : 'var(--brass)'}`,
                  background: free ? 'transparent' : 'var(--brass)',
                  color: free ? 'var(--muted)' : 'var(--abyss)',
                  fontSize: 11,
                  letterSpacing: '.08em',
                  textTransform: 'uppercase',
                  padding: '3px 9px',
                }}
              >
                {t(`tiers.${tier}`)}
              </span>
              {sub?.status && (
                <span className="num" style={{ fontSize: 11.5, color: 'var(--dim)' }}>
                  {t('status')}: {sub.status}
                </span>
              )}
            </div>
            {sub?.current_period_end && (
              <p className="num" style={{ margin: '9px 0 0', fontSize: 11.5, color: 'var(--dim)' }}>
                {sub.cancel_at_period_end ? t('endsOn') : t('renewsOn')}:{' '}
                {new Date(sub.current_period_end).toLocaleDateString(locale)}
              </p>
            )}
            {free && (
              <Link
                href={`/${locale}/pricing`}
                style={{
                  display: 'inline-block',
                  marginTop: 12,
                  background: 'var(--brass)',
                  color: 'var(--abyss)',
                  fontFamily: 'var(--font-ui)',
                  fontWeight: 600,
                  fontSize: 13,
                  padding: '8px 18px',
                  letterSpacing: '.02em',
                }}
              >
                {t('upgrade')}
              </Link>
            )}
          </div>
        </div>

        <button type="button" onClick={handleLogout} style={linkButtonStyle}>
          {t('logout')}
        </button>
      </main>
    );
  }

  // ----- Unauthenticated view: login / register form -----
  return (
    <main style={{ ...pageStyle, maxWidth: 520 }}>
      <header style={headerStyle}>
        <span className="eyebrow">{ru ? 'кабинет' : 'account'}</span>
        <h1 style={{ fontSize: 'clamp(26px,4.5vw,42px)', margin: '4px 0 0' }}>
          {mode === 'login' ? t('loginTitle') : t('registerTitle')}
        </h1>
        <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.6, marginTop: 10 }}>
          {mode === 'login' ? t('loginSubtitle') : t('registerSubtitle')}
        </p>
      </header>

      {error && (
        <p
          role="alert"
          style={{
            border: '1px solid var(--brass-dim)',
            background: 'var(--notice-bg)',
            color: 'var(--notice-ink)',
            padding: '10px 13px',
            fontSize: 13,
            lineHeight: 1.5,
            margin: '0 0 14px',
          }}
        >
          {error}
        </p>
      )}

      <form
        onSubmit={handleSubmit}
        style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px' }}
      >
        {mode === 'register' && (
          <Field label={t('name')} type="text" value={name} onChange={setName} autoComplete="name" />
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
          style={{
            width: '100%',
            marginTop: 12,
            background: 'var(--brass)',
            color: 'var(--abyss)',
            border: 0,
            fontFamily: 'var(--font-ui)',
            fontWeight: 600,
            padding: 10,
            letterSpacing: '.02em',
            cursor: busy ? 'not-allowed' : 'pointer',
            opacity: busy ? 0.45 : 1,
          }}
        >
          {busy ? t('submitting') : mode === 'login' ? t('loginCta') : t('registerCta')}
        </button>
      </form>

      <button
        type="button"
        onClick={() => {
          setMode(mode === 'login' ? 'register' : 'login');
          setError(null);
        }}
        style={linkButtonStyle}
      >
        {mode === 'login' ? t('switchToRegister') : t('switchToLogin')}
      </button>
    </main>
  );
}

// ── presentational helpers ──────────────────────────────────────────────────
const pageStyle: React.CSSProperties = {
  padding: 'clamp(14px,2.2vw,30px)',
  margin: '0 auto',
};
const headerStyle: React.CSSProperties = {
  paddingBottom: 14,
  marginBottom: 'clamp(12px,1.6vw,20px)',
  borderBottom: '1px solid var(--grat-1)',
};
const linkButtonStyle: React.CSSProperties = {
  marginTop: 14,
  background: 'transparent',
  border: 0,
  color: 'var(--muted)',
  fontFamily: 'var(--font-ui)',
  fontSize: 13,
  padding: 0,
  cursor: 'pointer',
  textDecoration: 'underline',
  textUnderlineOffset: 3,
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td style={{ color: 'var(--muted)', padding: '3px 0' }}>{label}</td>
      <td style={{ color: 'var(--parchment)', textAlign: 'right', padding: '3px 0' }}>{value}</td>
    </tr>
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
    <label style={{ display: 'block', marginBottom: 10 }}>
      <span
        style={{
          display: 'block',
          color: 'var(--dim)',
          fontFamily: 'var(--font-data)',
          fontSize: 10,
          letterSpacing: '.04em',
          textTransform: 'uppercase',
          margin: '0 0 3px',
        }}
      >
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required={required}
        style={{
          width: '100%',
          background: 'var(--abyss)',
          color: 'var(--parchment)',
          border: '1px solid var(--grat-2)',
          fontFamily: 'var(--font-ui)',
          fontSize: 13.5,
          padding: '8px 10px',
        }}
      />
      {hint && (
        <span style={{ display: 'block', marginTop: 3, fontSize: 11, color: 'var(--dim)' }}>
          {hint}
        </span>
      )}
    </label>
  );
}
