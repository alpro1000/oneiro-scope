import type {Metadata} from 'next';
import {format} from 'date-fns';
import {getTranslations, unstable_setRequestLocale} from 'next-intl/server';
import {getLunarDay} from '../../../../lib/lunar-server';
import LunarWidget from '../../../../components/LunarWidget';

export const metadata: Metadata = {
  alternates: {
    canonical: '/calendar'
  }
};

function formatDateForApi(date: Date): string {
  return format(date, 'yyyy-MM-dd');
}

export default async function CalendarPage({params}: {params: {locale: string}}) {
  const {locale} = params;
  unstable_setRequestLocale(locale);

  const today = new Date();
  const iso = formatDateForApi(today);
  const t = await getTranslations('CalendarPage');

  let initialError: string | null = null;
  let initial: Awaited<ReturnType<typeof getLunarDay>> | null = null;

  try {
    initial = await getLunarDay({locale, date: iso, tz: process.env.LUNAR_DEFAULT_TZ});
  } catch (error) {
    console.error('Failed to load initial lunar day', error);
    initialError = error instanceof Error ? error.message : 'Unknown error';
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col items-center gap-8 px-4 py-12">
      <header className="flex w-full flex-col items-center gap-2 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-gold sm:text-5xl">
          {t('title')}
        </h1>
        <p className="max-w-2xl text-base text-ink-muted sm:text-lg">{t('subtitle')}</p>
      </header>
      {initialError ? (
        <div className="w-full max-w-3xl rounded-lg border border-danger/40 bg-danger/5 p-6 text-center text-ink">
          <p className="text-lg font-semibold text-danger">{t('error.title')}</p>
          <p className="mt-2 text-sm text-ink-muted">{t('error.subtitle')}</p>
          <p className="mt-4 text-xs text-ink-muted">{initialError}</p>
          <p className="mt-6 text-sm text-ink-muted">{t('error.cta')}</p>
        </div>
      ) : (
        initial && <LunarWidget initialData={initial} locale={locale} />
      )}
    </main>
  );
}
