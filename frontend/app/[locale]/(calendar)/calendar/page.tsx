import type {Metadata} from 'next';
import {format} from 'date-fns';
import {unstable_setRequestLocale} from 'next-intl/server';
import {getLunarDay} from '../../../../lib/lunar-server';
import LunarInstrument from '../../../../components/LunarInstrument';

export const metadata: Metadata = {
  alternates: {canonical: '/calendar'}
};

const LUNAR_DEFAULT_TZ = process.env.LUNAR_DEFAULT_TZ || 'Europe/Moscow';

export default async function CalendarPage({params}: {params: {locale: string}}) {
  const {locale} = params;
  unstable_setRequestLocale(locale);
  const lang = locale === 'ru' ? 'ru' : 'en';
  const iso = format(new Date(), 'yyyy-MM-dd');

  let initial: Awaited<ReturnType<typeof getLunarDay>> | null = null;
  let err: string | null = null;
  try {
    initial = await getLunarDay({locale, date: iso, tz: LUNAR_DEFAULT_TZ});
  } catch (error) {
    // No mock fallback (conventions.md §12): if the server did not compute the
    // day, we say so rather than render an invented one.
    err = error instanceof Error ? error.message : 'Unknown error';
    console.error('Failed to load initial lunar day', error);
  }

  if (!initial) {
    const msg = lang === 'ru'
      ? 'Лунные данные недоступны: сервер не ответил. Расчёт делается на сервере, и мы не подменяем его выдумкой — попробуйте позже.'
      : 'Lunar data unavailable: the server did not answer. The computation is server-side and we do not substitute an invented one — try again later.';
    return (
      <main style={{padding: 'clamp(14px,2.2vw,30px)'}}>
        <div style={{
          border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)', color: 'var(--notice-ink)',
          padding: '16px 18px', maxWidth: '64ch', fontSize: 14, lineHeight: 1.6,
        }}>
          {msg}
          {err && <div className="num" style={{marginTop: 8, fontSize: 11, color: 'var(--dim)'}}>{err}</div>}
        </div>
      </main>
    );
  }

  return <LunarInstrument initial={initial} locale={locale} defaultTz={LUNAR_DEFAULT_TZ} />;
}
