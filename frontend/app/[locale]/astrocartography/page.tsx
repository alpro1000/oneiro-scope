'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import CityAutocomplete from '../../../components/CityAutocomplete';
import ConfidenceBadge from '../../../components/ConfidenceBadge';
import FindingCard from '../../../components/FindingCard';
import LoadingModal from '../../../components/LoadingModal';
import {
  getAstrocartographyChart,
  inspectAstrocartographyPoint,
  type AstrocartographyBirthInput,
  type AstrocartographyChartResponse,
  type AstrocartographyPointResponse,
} from '../../../lib/astrocartography-client';

const AstrocartographyMap = dynamic(() => import('../../../components/AstrocartographyMap'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-inkMuted">…</div>
  ),
});

const TIMEZONES = [
  'UTC',
  'Europe/London',
  'Europe/Madrid',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Rome',
  'Europe/Prague',
  'Europe/Bratislava',
  'Europe/Athens',
  'Europe/Kyiv',
  'Europe/Moscow',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
];

const PLANET_DATA: Record<string, { symbol: string; en: string; ru: string }> = {
  sun: { symbol: '☉', en: 'Sun', ru: 'Солнце' },
  moon: { symbol: '☽', en: 'Moon', ru: 'Луна' },
  mercury: { symbol: '☿', en: 'Mercury', ru: 'Меркурий' },
  venus: { symbol: '♀', en: 'Venus', ru: 'Венера' },
  mars: { symbol: '♂', en: 'Mars', ru: 'Марс' },
  jupiter: { symbol: '♃', en: 'Jupiter', ru: 'Юпитер' },
  saturn: { symbol: '♄', en: 'Saturn', ru: 'Сатурн' },
  uranus: { symbol: '♅', en: 'Uranus', ru: 'Уран' },
  neptune: { symbol: '♆', en: 'Neptune', ru: 'Нептун' },
  pluto: { symbol: '♇', en: 'Pluto', ru: 'Плутон' },
};

const PLANET_COLOR: Record<string, string> = {
  sun: '#f2a900',
  moon: '#5b8def',
  mercury: '#8a4fc4',
  venus: '#e8559a',
  mars: '#d23b2e',
  jupiter: '#1f9e3b',
  saturn: '#8a8f9c',
  uranus: '#00a8a8',
  neptune: '#2e86de',
  pluto: '#6c3483',
};

const ANGLE_KEYS = ['asc', 'mc', 'ic', 'desc'] as const;
const ANGLE_CONTACT_NAME: Record<(typeof ANGLE_KEYS)[number], 'Asc' | 'MC' | 'IC' | 'Desc'> = {
  asc: 'Asc',
  mc: 'MC',
  ic: 'IC',
  desc: 'Desc',
};

type City = { lat: number; lon: number; display: string };

export default function AstrocartographyPage() {
  const t = useTranslations('AstrocartographyPage');
  const params = useParams();
  const locale = (params?.locale as string) || 'ru';

  const [birthDate, setBirthDate] = useState('');
  const [birthTime, setBirthTime] = useState('');
  const [birthTimezone, setBirthTimezone] = useState('UTC');
  const [birthPlace, setBirthPlace] = useState('');
  const [birthCity, setBirthCity] = useState<City | null>(null);

  const [chart, setChart] = useState<AstrocartographyChartResponse | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);

  const [linesVisible, setLinesVisible] = useState(true);
  const [clickedPoint, setClickedPoint] = useState<{ lat: number; lon: number } | null>(null);
  const [pointResult, setPointResult] = useState<AstrocartographyPointResponse | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [inspectError, setInspectError] = useState<string | null>(null);

  const birthInput: AstrocartographyBirthInput | null = useMemo(() => {
    if (!birthCity || !birthDate) return null;
    return {
      birth_date: birthDate,
      birth_time: birthTime || undefined,
      birth_timezone: birthTimezone,
      birth_lat: birthCity.lat,
      birth_lon: birthCity.lon,
      birth_place: birthCity.display,
    };
  }, [birthDate, birthTime, birthTimezone, birthCity]);

  const handleBuild = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!birthInput) return;
    setIsBuilding(true);
    setBuildError(null);
    setPointResult(null);
    setClickedPoint(null);
    try {
      const result = await getAstrocartographyChart(birthInput);
      setChart(result);
    } catch (err) {
      setBuildError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsBuilding(false);
    }
  };

  const handleMapClick = async (lat: number, lon: number) => {
    if (!birthInput) return;
    setClickedPoint({ lat, lon });
    setIsInspecting(true);
    setInspectError(null);
    setPointResult(null);
    try {
      const result = await inspectAstrocartographyPoint(birthInput, { lat, lon, locale });
      setPointResult(result);
    } catch (err) {
      setInspectError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsInspecting(false);
    }
  };

  const planetName = (planet: string) => {
    const data = PLANET_DATA[planet.toLowerCase()];
    if (!data) return planet;
    return locale === 'ru' ? data.ru : data.en;
  };

  const seenText = useMemo(() => {
    if (!pointResult) return '';
    const parts = ANGLE_KEYS.map((key) => {
      const contacts = pointResult.contacts.filter((c) => c.angle === ANGLE_CONTACT_NAME[key]);
      if (contacts.length === 0) return null;
      const names = contacts.map((c) => `${planetName(c.planet)} ${c.orb_deg.toFixed(1)}°`).join(', ');
      return `${ANGLE_CONTACT_NAME[key]}: ${names}`;
    }).filter(Boolean);
    return parts.length > 0 ? parts.join(' · ') : t('noAngleContacts');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pointResult, locale]);

  return (
    <main className="oneiro-grid-bg min-h-screen bg-bg">
      <div className="pt-8 pb-12 px-4">
        <div className="container mx-auto max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="font-display text-3xl font-semibold text-ink mb-3 md:text-4xl">
              {t('title')}
            </h1>
            <p className="text-inkMuted">{t('subtitle')}</p>
          </motion.div>

          {/* Birth data form */}
          <motion.form
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            onSubmit={handleBuild}
            className="mx-auto mb-8 max-w-2xl rounded-lg border border-border bg-surface p-6"
          >
            <h2 className="mb-4 font-display text-lg font-semibold text-ink">{t('formTitle')}</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm text-inkMuted">{t('birthDate')} *</label>
                <input
                  type="date"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  required
                  className="w-full rounded-lg border border-border bg-bgDeep p-3 text-ink focus:outline-none focus:ring-2 focus:ring-gold"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm text-inkMuted">{t('birthTime')}</label>
                <input
                  type="time"
                  value={birthTime}
                  onChange={(e) => setBirthTime(e.target.value)}
                  className="w-full rounded-lg border border-border bg-bgDeep p-3 text-ink focus:outline-none focus:ring-2 focus:ring-gold"
                />
              </div>
            </div>
            <p className="mt-1 text-xs text-inkFaint">{t('unknownTime')}</p>

            <div className="mt-4">
              <label className="mb-1 block text-sm text-inkMuted">{t('birthTimezone')} *</label>
              <select
                value={birthTimezone}
                onChange={(e) => setBirthTimezone(e.target.value)}
                className="w-full rounded-lg border border-border bg-bgDeep p-3 text-ink focus:outline-none focus:ring-2 focus:ring-gold"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-4">
              <label className="mb-1 block text-sm text-inkMuted">{t('birthPlace')} *</label>
              <CityAutocomplete
                value={birthPlace}
                onChange={setBirthPlace}
                onCitySelect={(city) =>
                  setBirthCity({ lat: city.lat, lon: city.lon, display: city.display })
                }
                placeholder={locale === 'ru' ? 'Москва, Россия' : 'Moscow, Russia'}
                locale={locale}
              />
            </div>

            <button
              type="submit"
              disabled={!birthInput || isBuilding}
              className="mt-5 w-full rounded-full bg-gold py-3 font-semibold text-bgDeep transition-colors hover:bg-goldStrong disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isBuilding ? t('building') : t('buildButton')}
            </button>

            {buildError && (
              <p role="alert" className="mt-3 text-sm text-danger">
                {t('buildError')}: {buildError}
              </p>
            )}
          </motion.form>

          {/* Map + result panel */}
          {chart && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]"
            >
              <div className="relative h-[420px] overflow-hidden rounded-lg border border-border sm:h-[520px]">
                <AstrocartographyMap
                  lines={chart.lines.features}
                  linesVisible={linesVisible}
                  birthMarker={{
                    lat: chart.chart.birth.lat,
                    lon: chart.chart.birth.lon,
                    label: chart.chart.birth.name,
                  }}
                  clickedPoint={clickedPoint ?? undefined}
                  onMapClick={handleMapClick}
                />
                <button
                  type="button"
                  onClick={() => setLinesVisible((prev) => !prev)}
                  className="absolute right-3 top-3 z-[500] rounded-full border border-border bg-surfaceStrong/90 px-3 py-1.5 text-xs font-medium text-ink backdrop-blur hover:bg-surface"
                >
                  {linesVisible ? t('hideLines') : t('showLines')}
                </button>
                <div className="absolute bottom-3 left-3 z-[500] max-w-[70%] rounded-lg border border-border bg-surfaceStrong/90 p-2 text-[11px] text-inkMuted backdrop-blur">
                  <b className="text-ink">{t('legendTitle')}</b>
                  <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5">
                    {Object.keys(PLANET_DATA).map((p) => (
                      <span key={p}>
                        <span
                          className="mr-1 inline-block h-[3px] w-2.5 align-middle"
                          style={{ background: PLANET_COLOR[p] }}
                        />
                        {PLANET_DATA[p].symbol} {planetName(p)}
                      </span>
                    ))}
                  </div>
                  <div className="mt-1">{t('legendLines')}</div>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-surface p-5">
                {!clickedPoint && (
                  <p className="text-sm text-inkMuted">{t('hint')}</p>
                )}

                {isInspecting && <p className="text-sm text-inkMuted">{t('inspecting')}</p>}

                {inspectError && (
                  <p role="alert" className="text-sm text-danger">
                    {t('inspectError')}: {inspectError}
                  </p>
                )}

                {pointResult && !isInspecting && (
                  <div className="flex flex-col gap-4">
                    <ConfidenceBadge
                      score={pointResult.summary.confidence}
                      source={pointResult.summary.source}
                    />
                    <FindingCard
                      title={t('resultTitle')}
                      seenLabel={t('seenLabel')}
                      seenText={seenText}
                      traditionQuote={pointResult.summary.plain}
                      traditionSource={t('traditionSource')}
                      plusLabel={t('plusLabel')}
                      plusText={
                        [...pointResult.summary.work, ...pointResult.summary.home, ...pointResult.summary.luck]
                          .map(planetName)
                          .join(', ') || undefined
                      }
                      minusLabel={t('minusLabel')}
                      minusText={pointResult.summary.tension.map(planetName).join(', ') || undefined}
                    />
                    {pointResult.summary.clean && (
                      <p className="rounded-md border border-gold bg-goldSoft px-3 py-2 text-sm text-ink">
                        ✅ {t('cleanLuck')}
                      </p>
                    )}

                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {ANGLE_KEYS.map((key) => {
                        const angleName = ANGLE_CONTACT_NAME[key];
                        const contacts = pointResult.contacts.filter((c) => c.angle === angleName);
                        return (
                          <div key={key} className="rounded-md border border-border bg-surfaceStrong p-3">
                            <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-goldStrong">
                              {t(`angles.${key}`)}
                            </h4>
                            <p className="mt-0.5 text-xs text-inkFaint">{t(`angleDesc.${key}`)}</p>
                            {contacts.length > 0 ? (
                              <ul className="mt-2 space-y-1 text-sm text-inkMuted">
                                {contacts.map((c, i) => (
                                  <li key={i} className="flex items-center gap-1.5">
                                    <span
                                      className="inline-block h-2 w-2 rounded-full"
                                      style={{ background: PLANET_COLOR[c.planet.toLowerCase()] || '#8a7dff' }}
                                    />
                                    {planetName(c.planet)}
                                    <span className="ml-auto font-mono text-xs text-inkFaint">
                                      {c.orb_deg.toFixed(1)}°
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-2 text-xs italic text-inkFaint">{t('noAngleContacts')}</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                <p className="mt-6 border-t border-border pt-3 text-[11px] leading-relaxed text-inkFaint">
                  {t('disclaimer')}
                </p>
              </div>
            </motion.div>
          )}

          <div className="mt-8 text-center">
            <Link href={`/${locale}`} className="text-inkMuted transition-colors hover:text-gold">
              ← {locale === 'ru' ? 'На главную' : 'Back to Home'}
            </Link>
          </div>
        </div>
      </div>

      <LoadingModal isOpen={isBuilding} message={locale === 'ru' ? 'Считаем линии...' : 'Computing lines...'} />
    </main>
  );
}
