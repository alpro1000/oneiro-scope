'use client';

import {useEffect, useMemo, useRef, useState} from 'react';
import {AnimatePresence, motion} from 'framer-motion';
import {useTranslations} from 'next-intl';
import {fetchLunarDayClient} from '../lib/lunar-client';
import type {LunarDayPayload} from '../lib/lunar-server';

function formatDateLabel(dateIso: string, locale: string): string {
  const date = new Date(dateIso);
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  }).format(date);
}

function getMonthDateList(currentIso: string): string[] {
  const current = new Date(currentIso);
  const first = new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth(), 1));
  const totalDays = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();

  const list: string[] = [];
  for (let day = 1; day <= totalDays; day += 1) {
    const date = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), day));
    const iso = date.toISOString().slice(0, 10);
    list.push(iso);
  }
  return list;
}

type Props = {
  initialData: LunarDayPayload;
  locale: string;
};

type Status = 'idle' | 'loading' | 'ready' | 'error';

export default function LunarWidget({initialData, locale}: Props) {
  const t = useTranslations('LunarWidget');
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState<Status>('idle');
  const [monthData, setMonthData] = useState<LunarDayPayload[]>([]);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Map<string, LunarDayPayload>>(new Map([[initialData.date, initialData]]));

  const formattedDate = useMemo(
    () => formatDateLabel(initialData.date, locale),
    [initialData.date, locale]
  );

  useEffect(() => {
    if (!expanded || status !== 'idle') {
      return;
    }

    if (monthData.length > 0) {
      setStatus('ready');
      return;
    }

    let cancelled = false;
    const loadMonth = async () => {
      try {
        setStatus('loading');
        setError(null);
        const dates = getMonthDateList(initialData.date);
        const promises = dates.map(async (iso) => {
          const cached = cacheRef.current.get(iso);
          if (cached) {
            return cached;
          }
          const response = await fetchLunarDayClient(iso, locale);
          cacheRef.current.set(response.date, response);
          return response;
        });
        const resolved = await Promise.all(promises);
        if (!cancelled) {
          const sorted = [...resolved].sort((a, b) => a.date.localeCompare(b.date));
          setMonthData(sorted);
          setStatus('ready');
        }
      } catch (err) {
        if (!cancelled) {
          setStatus('error');
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      }
    };

    loadMonth();

    return () => {
      cancelled = true;
    };
  }, [expanded, initialData.date, locale, monthData.length, status]);

  useEffect(() => {
    if (!expanded) {
      setStatus('idle');
    }
  }, [expanded]);

  const isLoading = status === 'loading';
  const monthRows = expanded && status === 'ready' ? monthData : [];

  return (
    <section
      className="w-full max-w-3xl rounded-lg border border-gold-soft bg-surface p-6 shadow-gold backdrop-blur-lg transition-[box-shadow,transform] duration-lunar ease-lunar hover:shadow-[0_32px_64px_-28px_rgba(195,165,106,0.75)]"
      aria-live="polite"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-2">
            <span className="text-sm uppercase tracking-[0.3em] text-gold">{t('phase')}</span>
            <h2 className="text-3xl font-semibold text-ink">
              {initialData.phase}
            </h2>
            <p className="text-sm text-ink-muted">{t('updated', {date: formattedDate})}</p>
          </div>
          <div className="flex flex-col items-start gap-2 rounded-md border border-gold-soft bg-surfaceStrong px-4 py-3">
            <span className="text-xs font-medium uppercase tracking-[0.25em] text-gold">{t('lunarDay', {day: initialData.lunar_day})}</span>
            <span className="text-sm text-ink-muted">{initialData.description}</span>
          </div>
        </div>
        <div className="rounded-md border border-gold-soft bg-surfaceStrong p-4 text-sm leading-relaxed text-ink">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-gold">{t('recommendation')}</h3>
          <p>{initialData.recommendation}</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 self-start rounded-full border border-gold px-4 py-2 text-sm font-medium text-gold transition-colors duration-lunar ease-lunar hover:bg-gold hover:text-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? t('hideMonth') : t('showMonth')}
        </button>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="lunar-month"
            initial={{height: 0, opacity: 0}}
            animate={{height: 'auto', opacity: 1}}
            exit={{height: 0, opacity: 0}}
            transition={{duration: 0.3, ease: 'easeInOut'}}
            className="overflow-hidden"
          >
            <div className="mt-6 rounded-lg border border-gold-soft bg-surfaceStrong p-4">
              {isLoading && <p className="text-sm text-ink-muted">{t('loading')}</p>}
              {status === 'error' && (
                <p role="alert" className="text-sm text-danger">
                  {t('error')}
                  {error ? ` — ${error}` : ''}
                </p>
              )}
              {status === 'ready' && (
                <div className="relative overflow-x-auto">
                  <table className="w-full min-w-[560px] table-fixed border-collapse text-left text-sm">
                    <thead className="text-xs uppercase tracking-[0.2em] text-gold">
                      <tr>
                        <th className="py-2 pr-4">{t('tableDate')}</th>
                        <th className="py-2 pr-4">{t('tableDay')}</th>
                        <th className="py-2 pr-4">{t('tableDescription')}</th>
                        <th className="py-2">{t('tableRecommendation')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {monthRows.map((day) => {
                        const isToday = day.date === initialData.date;
                        return (
                          <tr
                            key={day.date}
                            data-testid={`row-${day.date}`}
                            className={
                              'border-t border-[color:rgba(195,165,106,0.4)] transition-colors duration-200 ease-in-out' +
                              (isToday
                                ? ' bg-[color:rgba(195,165,106,0.25)] text-ink'
                                : ' hover:bg-[color:rgba(195,165,106,0.12)]')
                            }
                            aria-current={isToday ? 'date' : undefined}
                          >
                            <td className="py-2 pr-4 align-top" data-testid={`date-${day.date}`}>
                              {formatDateLabel(day.date, locale)}
                            </td>
                            <td className="py-2 pr-4 align-top font-medium text-gold">{day.lunar_day}</td>
                            <td className="py-2 pr-4 align-top text-ink-muted">{day.description}</td>
                            <td className="py-2 align-top text-ink">{day.recommendation}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
