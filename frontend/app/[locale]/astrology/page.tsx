'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  calculateNatalChart,
  getHoroscope,
  forecastEvent,
  getEventTypes,
  type NatalChartResponse,
  type HoroscopeResponse,
  type EventForecastResponse,
  type TransitInfo,
} from '../../../lib/astrology-client';
import LoadingModal from '../../../components/LoadingModal';
import CityAutocomplete from '../../../components/CityAutocomplete';
import ConfidenceBadge from '../../../components/ConfidenceBadge';
import FindingCard from '../../../components/FindingCard';
import NatalWheel from '../../../components/NatalWheel';

type Tab = 'natalChart' | 'horoscope' | 'eventForecast';

// Planet symbols and display names
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
  north_node: { symbol: '☊', en: 'North Node', ru: 'Сев. Узел' },
  south_node: { symbol: '☋', en: 'South Node', ru: 'Юж. Узел' },
  chiron: { symbol: '⚷', en: 'Chiron', ru: 'Хирон' },
};

// Zodiac sign symbols and display names
const SIGN_DATA: Record<string, { symbol: string; en: string; ru: string }> = {
  aries: { symbol: '♈', en: 'Aries', ru: 'Овен' },
  taurus: { symbol: '♉', en: 'Taurus', ru: 'Телец' },
  gemini: { symbol: '♊', en: 'Gemini', ru: 'Близнецы' },
  cancer: { symbol: '♋', en: 'Cancer', ru: 'Рак' },
  leo: { symbol: '♌', en: 'Leo', ru: 'Лев' },
  virgo: { symbol: '♍', en: 'Virgo', ru: 'Дева' },
  libra: { symbol: '♎', en: 'Libra', ru: 'Весы' },
  scorpio: { symbol: '♏', en: 'Scorpio', ru: 'Скорпион' },
  sagittarius: { symbol: '♐', en: 'Sagittarius', ru: 'Стрелец' },
  capricorn: { symbol: '♑', en: 'Capricorn', ru: 'Козерог' },
  aquarius: { symbol: '♒', en: 'Aquarius', ru: 'Водолей' },
  pisces: { symbol: '♓', en: 'Pisces', ru: 'Рыбы' },
};

// Aspect type display names — cited nowhere per-aspect in the backend,
// so the FindingCard source caption stays a generic "по натальным
// транзитам" rather than inventing a citation.
const ASPECT_LABEL: Record<string, { en: string; ru: string }> = {
  conjunction: { en: 'conjunction', ru: 'соединение' },
  sextile: { en: 'sextile', ru: 'секстиль' },
  square: { en: 'square', ru: 'квадрат' },
  trine: { en: 'trine', ru: 'трин' },
  opposition: { en: 'opposition', ru: 'оппозиция' },
  quincunx: { en: 'quincunx', ru: 'квинконс' },
};

export default function AstrologyPage() {
  const t = useTranslations('AstrologyPage');
  const params = useParams();
  const locale = (params.locale as string) || 'ru';

  const [activeTab, setActiveTab] = useState<Tab>('natalChart');

  // Natal chart form
  const [birthDate, setBirthDate] = useState('');
  const [birthTime, setBirthTime] = useState('');
  const [birthPlace, setBirthPlace] = useState('');
  const [isCalculating, setIsCalculating] = useState(false);
  const [natalResult, setNatalResult] = useState<NatalChartResponse | null>(null);
  const [natalError, setNatalError] = useState<string | null>(null);

  // Event forecast form
  const [eventDate, setEventDate] = useState('');
  const [eventType, setEventType] = useState('travel');
  const [eventLocation, setEventLocation] = useState('');
  const [forecastResult, setForecastResult] = useState<EventForecastResponse | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);

  // Horoscope
  const [horoscopePeriod, setHoroscopePeriod] = useState<'daily' | 'weekly' | 'monthly' | 'yearly'>('daily');
  const [horoscopeResult, setHoroscopeResult] = useState<HoroscopeResponse | null>(null);
  const [horoscopeError, setHoroscopeError] = useState<string | null>(null);

  // Event types from API
  const [eventTypes, setEventTypes] = useState<Array<{ value: string; label_en: string; label_ru: string }>>([]);

  const horoscopePeriods = ['daily', 'weekly', 'monthly', 'yearly'] as const;

  const tabs: { id: Tab; label: string }[] = [
    { id: 'natalChart', label: t('tabs.natalChart') },
    { id: 'horoscope', label: t('tabs.horoscope') },
    { id: 'eventForecast', label: t('tabs.eventForecast') },
  ];

  // Default event types as fallback
  const defaultEventTypes = [
    { value: 'travel', label_en: 'Travel', label_ru: 'Путешествие' },
    { value: 'wedding', label_en: 'Wedding', label_ru: 'Свадьба' },
    { value: 'business', label_en: 'Business Deal', label_ru: 'Бизнес-сделка' },
    { value: 'interview', label_en: 'Interview', label_ru: 'Собеседование' },
    { value: 'surgery', label_en: 'Surgery', label_ru: 'Операция' },
    { value: 'moving', label_en: 'Moving', label_ru: 'Переезд' },
    { value: 'contract', label_en: 'Contract Signing', label_ru: 'Подписание контракта' },
    { value: 'exam', label_en: 'Exam', label_ru: 'Экзамен' },
    { value: 'date', label_en: 'Date', label_ru: 'Свидание' },
  ];

  // Load event types from API on mount
  useEffect(() => {
    getEventTypes()
      .then((data) => setEventTypes(data.event_types))
      .catch(() => setEventTypes(defaultEventTypes));
  }, []);

  const displayEventTypes = eventTypes.length > 0 ? eventTypes : defaultEventTypes;

  const transitCardProps = (transit: TransitInfo) => {
    const ru = locale === 'ru';
    const from = PLANET_DATA[transit.transiting_planet?.toLowerCase()] || {symbol: '●', en: transit.transiting_planet, ru: transit.transiting_planet};
    const to = PLANET_DATA[transit.natal_planet?.toLowerCase()] || {symbol: '●', en: transit.natal_planet, ru: transit.natal_planet};
    const aspect = ASPECT_LABEL[transit.aspect?.toLowerCase()] || {en: transit.aspect, ru: transit.aspect};
    return {
      title: `${from.symbol} ${ru ? from.ru : from.en} — ${ru ? aspect.ru : aspect.en} — ${to.symbol} ${ru ? to.ru : to.en}`,
      seenLabel: ru ? 'Система увидела' : 'System saw',
      seenText: ru
        ? `орбис ${transit.orb}° · точная дата ${transit.exact_date}`
        : `orb ${transit.orb}° · exact date ${transit.exact_date}`,
      traditionQuote: transit.description,
      traditionSource: ru ? 'по натальным транзитам' : 'natal transit reading',
    };
  };

  const handleCalculateNatalChart = async () => {
    if (!birthDate || !birthPlace) return;

    setIsCalculating(true);
    setNatalError(null);

    try {
      const result = await calculateNatalChart({
        birth_date: birthDate,
        birth_time: birthTime || undefined,
        birth_place: birthPlace,
        locale,
      });
      setNatalResult(result);
    } catch (error) {
      setNatalError(error instanceof Error ? error.message : 'Failed to calculate natal chart');
      setNatalResult(null);
    } finally {
      setIsCalculating(false);
    }
  };

  const handleGetHoroscope = async () => {
    setIsCalculating(true);
    setHoroscopeError(null);

    try {
      const result = await getHoroscope({
        period: horoscopePeriod,
        locale,
      });
      setHoroscopeResult(result);
    } catch (error) {
      setHoroscopeError(error instanceof Error ? error.message : 'Failed to get horoscope');
      setHoroscopeResult(null);
    } finally {
      setIsCalculating(false);
    }
  };

  const handleGetForecast = async () => {
    if (!eventDate) return;

    setIsCalculating(true);
    setForecastError(null);

    try {
      const result = await forecastEvent({
        event_date: eventDate,
        event_type: eventType,
        event_location: eventLocation || undefined,
        locale,
      });
      setForecastResult(result);
    } catch (error) {
      setForecastError(error instanceof Error ? error.message : 'Failed to get forecast');
      setForecastResult(null);
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <main className="oneiro-grid-bg min-h-screen bg-bg">
      {/* Site-wide nav/theme/language now come from the shared Header
          in the root layout — this page no longer duplicates it. */}

      {/* Content */}
      <div className="pt-8 pb-12 px-4">
        <div className="container mx-auto max-w-3xl">
          {/* Title */}
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

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex justify-center gap-1 mb-8 rounded-full border border-border bg-surface p-1 w-fit mx-auto flex-wrap"
          >
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? 'true' : undefined}
                className={`
                  px-4 py-2 rounded-full text-sm font-medium
                  transition-colors duration-200
                  ${
                    activeTab === tab.id
                      ? 'bg-gold text-bgDeep'
                      : 'text-inkMuted hover:text-ink'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </motion.div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            {/* Natal Chart Tab */}
            {activeTab === 'natalChart' && (
              <motion.div
                key="natalChart"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="rounded-2xl border border-border bg-surface p-6"
              >
                <h2 className="font-display text-xl font-semibold text-ink mb-6">
                  {t('natalChart.title')}
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-inkMuted text-sm mb-2">
                      {t('natalChart.birthDate')} *
                    </label>
                    <input
                      type="date"
                      value={birthDate}
                      onChange={(e) => setBirthDate(e.target.value)}
                      className="w-full p-3 bg-bgDeep border border-border rounded-lg text-ink focus:outline-none focus:ring-2 focus:ring-gold"
                    />
                  </div>

                  <div>
                    <label className="block text-inkMuted text-sm mb-2">
                      {t('natalChart.birthTime')}
                    </label>
                    <input
                      type="time"
                      value={birthTime}
                      onChange={(e) => setBirthTime(e.target.value)}
                      className="w-full p-3 bg-bgDeep border border-border rounded-lg text-ink focus:outline-none focus:ring-2 focus:ring-gold"
                    />
                    <p className="text-inkFaint text-xs mt-1">
                      {t('natalChart.unknownTime')}
                    </p>
                  </div>

                  <div>
                    <label className="block text-inkMuted text-sm mb-2">
                      {t('natalChart.birthPlace')} *
                    </label>
                    <CityAutocomplete
                      value={birthPlace}
                      onChange={setBirthPlace}
                      placeholder={locale === 'ru' ? 'Москва, Россия' : 'Moscow, Russia'}
                      locale={locale}
                      disabled={isCalculating}
                    />
                  </div>

                  <button
                    onClick={handleCalculateNatalChart}
                    disabled={!birthDate || !birthPlace || isCalculating}
                    className="w-full py-3 rounded-full bg-gold text-bgDeep font-semibold transition-colors hover:bg-goldStrong disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {isCalculating ? (
                      <motion.div
                        className="w-5 h-5 border-2 border-bgDeep border-t-transparent rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      />
                    ) : (
                      <span>⭐</span>
                    )}
                    {t('natalChart.calculateButton')}
                  </button>
                </div>

                {/* Error */}
                {natalError && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-danger/10 border border-danger/30 rounded-xl"
                  >
                    <p className="text-danger">{natalError}</p>
                  </motion.div>
                )}

                {/* Result */}
                {natalResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 rounded-xl border border-border bg-surfaceStrong"
                  >
                    <div className="mb-4">
                      <ConfidenceBadge
                        score={birthTime ? 1.0 : 0.85}
                        source={
                          birthTime
                            ? (locale === 'ru' ? 'расчёт по эфемеридам · точное время рождения' : 'ephemeris calculation · exact birth time')
                            : (locale === 'ru' ? 'расчёт по эфемеридам · время рождения не указано, дома/асцендент недоступны' : 'ephemeris calculation · no birth time, houses/ascendant unavailable')
                        }
                      />
                    </div>

                    {natalResult.planets && natalResult.planets.length > 0 && (
                      <div className="mb-4 flex justify-center rounded-lg border border-border bg-surface p-3">
                        <NatalWheel
                          planets={natalResult.planets}
                          aspects={natalResult.aspects || []}
                          ascendantSign={natalResult.ascendant}
                        />
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4 mb-4 sm:grid-cols-4">
                      <div className="rounded-lg border border-border bg-surface p-3">
                        <span className="font-mono text-[0.62rem] uppercase tracking-widest text-inkFaint">☉ {locale === 'ru' ? 'Солнце' : 'Sun'}</span>
                        <p className="font-display font-semibold text-ink mt-1">
                          {(() => {
                            const signInfo = SIGN_DATA[natalResult.sun_sign?.toLowerCase()] || { symbol: '', en: natalResult.sun_sign, ru: natalResult.sun_sign };
                            return `${signInfo.symbol} ${locale === 'ru' ? signInfo.ru : signInfo.en}`;
                          })()}
                        </p>
                      </div>
                      <div className="rounded-lg border border-border bg-surface p-3">
                        <span className="font-mono text-[0.62rem] uppercase tracking-widest text-inkFaint">☽ {locale === 'ru' ? 'Луна' : 'Moon'}</span>
                        <p className="font-display font-semibold text-ink mt-1">
                          {(() => {
                            const signInfo = SIGN_DATA[natalResult.moon_sign?.toLowerCase()] || { symbol: '', en: natalResult.moon_sign, ru: natalResult.moon_sign };
                            return `${signInfo.symbol} ${locale === 'ru' ? signInfo.ru : signInfo.en}`;
                          })()}
                        </p>
                      </div>
                      {natalResult.ascendant && (
                        <div className="rounded-lg border border-border bg-surface p-3">
                          <span className="font-mono text-[0.62rem] uppercase tracking-widest text-inkFaint">ASC {locale === 'ru' ? 'Асцендент' : 'Ascendant'}</span>
                          <p className="font-display font-semibold text-ink mt-1">
                            {(() => {
                              const signInfo = SIGN_DATA[natalResult.ascendant?.toLowerCase()] || { symbol: '', en: natalResult.ascendant, ru: natalResult.ascendant };
                              return `${signInfo.symbol} ${locale === 'ru' ? signInfo.ru : signInfo.en}`;
                            })()}
                          </p>
                        </div>
                      )}
                      {natalResult.midheaven && (
                        <div className="rounded-lg border border-border bg-surface p-3">
                          <span className="font-mono text-[0.62rem] uppercase tracking-widest text-inkFaint">MC {locale === 'ru' ? 'Середина неба' : 'Midheaven'}</span>
                          <p className="font-display font-semibold text-ink mt-1">
                            {(() => {
                              const signInfo = SIGN_DATA[natalResult.midheaven?.toLowerCase()] || { symbol: '', en: natalResult.midheaven, ru: natalResult.midheaven };
                              return `${signInfo.symbol} ${locale === 'ru' ? signInfo.ru : signInfo.en}`;
                            })()}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Planet positions */}
                    {natalResult.planets && natalResult.planets.length > 0 && (
                      <div className="mb-4 rounded-lg border border-border bg-surface p-3">
                        <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-inkFaint mb-2">
                          {locale === 'ru' ? 'Планеты' : 'Planets'}
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                          {natalResult.planets.slice(0, 10).map((planet: any) => {
                            // Get planet key - backend returns 'planet' field with lowercase values
                            const planetKey = planet.planet || planet.name || '';
                            const planetInfo = PLANET_DATA[planetKey.toLowerCase()] || { symbol: '●', en: planetKey, ru: planetKey };
                            // Get sign key - backend returns lowercase sign values
                            const signKey = planet.sign || '';
                            const signInfo = SIGN_DATA[signKey.toLowerCase()] || { symbol: '', en: signKey, ru: signKey };

                            return (
                              <div key={planetKey} className="flex items-center gap-1 text-inkMuted">
                                <span className="text-gold">{planetInfo.symbol}</span>
                                <span>{locale === 'ru' ? planetInfo.ru : planetInfo.en}</span>
                                <span className="text-goldStrong">
                                  {signInfo.symbol} {locale === 'ru' ? signInfo.ru : signInfo.en}
                                </span>
                                {planet.retrograde && <span className="text-danger">℞</span>}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Aspects — fetched but previously unrendered */}
                    {natalResult.aspects && natalResult.aspects.length > 0 && (
                      <div className="mb-4 rounded-lg border border-border bg-surface p-3">
                        <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-inkFaint mb-2">
                          {locale === 'ru' ? 'Аспекты' : 'Aspects'}
                        </h4>
                        <div className="space-y-1 text-sm">
                          {natalResult.aspects.slice(0, 8).map((aspect: any, i: number) => {
                            const p1 = PLANET_DATA[aspect.planet1?.toLowerCase()] || {symbol: '●', en: aspect.planet1, ru: aspect.planet1};
                            const p2 = PLANET_DATA[aspect.planet2?.toLowerCase()] || {symbol: '●', en: aspect.planet2, ru: aspect.planet2};
                            const asp = ASPECT_LABEL[aspect.aspect_type?.toLowerCase()] || {en: aspect.aspect_type, ru: aspect.aspect_type};
                            return (
                              <div key={i} className="flex items-center gap-2 text-inkMuted">
                                <span>{p1.symbol} {locale === 'ru' ? p1.ru : p1.en}</span>
                                <span className="text-goldStrong">{locale === 'ru' ? asp.ru : asp.en}</span>
                                <span>{p2.symbol} {locale === 'ru' ? p2.ru : p2.en}</span>
                                <span className="font-mono text-xs text-inkFaint">{aspect.orb}°</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {natalResult.interpretation && (
                      <p className="text-inkMuted">{natalResult.interpretation}</p>
                    )}
                  </motion.div>
                )}
              </motion.div>
            )}

            {/* Horoscope Tab */}
            {activeTab === 'horoscope' && (
              <motion.div
                key="horoscope"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="rounded-2xl border border-border bg-surface p-6"
              >
                <h2 className="font-display text-xl font-semibold text-ink mb-6">
                  {t('horoscope.title')}
                </h2>

                <div className="flex gap-1 mb-6 rounded-full border border-border bg-bgDeep p-1 w-fit flex-wrap">
                  {horoscopePeriods.map((period) => (
                    <button
                      key={period}
                      onClick={() => setHoroscopePeriod(period)}
                      className={`px-4 py-2 rounded-full text-sm transition-colors ${
                        horoscopePeriod === period
                          ? 'bg-gold text-bgDeep'
                          : 'text-inkMuted hover:text-ink'
                      }`}
                    >
                      {t(`horoscope.${period}`)}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleGetHoroscope}
                  disabled={isCalculating}
                  className="w-full py-3 rounded-full bg-gold text-bgDeep font-semibold transition-colors hover:bg-goldStrong disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isCalculating ? (
                    <motion.div
                      className="w-5 h-5 border-2 border-bgDeep border-t-transparent rounded-full"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                  ) : (
                    <span>✨</span>
                  )}
                  {locale === 'ru' ? 'Получить гороскоп' : 'Get Horoscope'}
                </button>

                {/* Error */}
                {horoscopeError && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-danger/10 border border-danger/30 rounded-xl"
                  >
                    <p className="text-danger">{horoscopeError}</p>
                  </motion.div>
                )}

                {horoscopeResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 rounded-xl border border-border bg-surfaceStrong"
                  >
                    {/* Lunar info */}
                    <div className="mb-4 rounded-md border border-border bg-bgDeep px-3 py-2 font-mono text-xs text-inkMuted">
                      ☽ {horoscopeResult.lunar_phase}
                      {' · '}{locale === 'ru' ? `день ${horoscopeResult.lunar_day}` : `day ${horoscopeResult.lunar_day}`}
                      {horoscopeResult.retrograde_planets.length > 0 && (
                        <span className="text-goldStrong">
                          {' · ℞ '}{horoscopeResult.retrograde_planets.join(', ')}
                        </span>
                      )}
                    </div>

                    <p className="text-inkMuted mb-4">{horoscopeResult.summary}</p>

                    {/* Transits — fetched but previously unrendered */}
                    {horoscopeResult.transits && horoscopeResult.transits.length > 0 && (
                      <div className="mb-4">
                        <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-inkFaint mb-3">
                          {locale === 'ru' ? 'Активные транзиты' : 'Active transits'}
                        </h4>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          {horoscopeResult.transits.slice(0, 4).map((transit, i) => (
                            <FindingCard key={i} {...transitCardProps(transit)} />
                          ))}
                        </div>
                      </div>
                    )}

                    {horoscopeResult.recommendations && horoscopeResult.recommendations.length > 0 && (
                      <>
                        <h4 className="font-display font-semibold text-ink mb-2">
                          {t('eventForecast.recommendations')}:
                        </h4>
                        <ul className="space-y-2">
                          {horoscopeResult.recommendations.map((rec: string, i: number) => (
                            <li key={i} className="text-inkMuted flex items-start gap-2">
                              <span className="text-gold">—</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </motion.div>
                )}
              </motion.div>
            )}

            {/* Event Forecast Tab */}
            {activeTab === 'eventForecast' && (
              <motion.div
                key="eventForecast"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="rounded-2xl border border-border bg-surface p-6"
              >
                <h2 className="font-display text-xl font-semibold text-ink mb-6">
                  {t('eventForecast.title')}
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-inkMuted text-sm mb-2">
                      {t('eventForecast.eventDate')} *
                    </label>
                    <input
                      type="date"
                      value={eventDate}
                      onChange={(e) => setEventDate(e.target.value)}
                      className="w-full p-3 bg-bgDeep border border-border rounded-lg text-ink focus:outline-none focus:ring-2 focus:ring-gold"
                    />
                  </div>

                  <div>
                    <label className="block text-inkMuted text-sm mb-2">
                      {t('eventForecast.eventType')}
                    </label>
                    <select
                      value={eventType}
                      onChange={(e) => setEventType(e.target.value)}
                      className="w-full p-3 bg-bgDeep border border-border rounded-lg text-ink focus:outline-none focus:ring-2 focus:ring-gold"
                    >
                      {displayEventTypes.map((type) => (
                        <option key={type.value} value={type.value}>
                          {locale === 'ru' ? type.label_ru : type.label_en}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-inkMuted text-sm mb-2">
                      {t('eventForecast.eventLocation')}
                    </label>
                    <CityAutocomplete
                      value={eventLocation}
                      onChange={setEventLocation}
                      placeholder={locale === 'ru' ? 'Париж, Франция' : 'Paris, France'}
                      locale={locale}
                      disabled={isCalculating}
                    />
                  </div>

                  <button
                    onClick={handleGetForecast}
                    disabled={!eventDate || isCalculating}
                    className="w-full py-3 rounded-full bg-gold text-bgDeep font-semibold transition-colors hover:bg-goldStrong disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isCalculating ? (
                      <motion.div
                        className="w-5 h-5 border-2 border-bgDeep border-t-transparent rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      />
                    ) : (
                      <span>🔮</span>
                    )}
                    {t('eventForecast.forecastButton')}
                  </button>
                </div>

                {/* Error */}
                {forecastError && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-danger/10 border border-danger/30 rounded-xl"
                  >
                    <p className="text-danger">{forecastError}</p>
                  </motion.div>
                )}

                {/* Forecast Result */}
                {forecastResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 rounded-xl border border-border bg-surfaceStrong"
                  >
                    {/* Favorability Score — a gauge, matching the mockup's
                        event-forecast screen; semantic tone (not the
                        page accent) since this genuinely is a good/bad
                        signal. */}
                    <div className="mb-6">
                      <div className="flex items-baseline gap-3 flex-wrap">
                        <span className="font-display text-3xl font-semibold text-goldStrong">
                          {forecastResult.favorability_score}%
                        </span>
                        <span className="text-inkMuted">{forecastResult.favorability_level}</span>
                      </div>
                      <div className="relative h-2.5 rounded-full mt-3 overflow-hidden bg-border">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${forecastResult.favorability_score}%` }}
                          className={`h-full rounded-full ${
                            forecastResult.favorability_score >= 70
                              ? 'bg-gold'
                              : forecastResult.favorability_score >= 40
                              ? 'bg-goldSoft'
                              : 'bg-danger'
                          }`}
                        />
                      </div>
                    </div>

                    {/* Factors — flat strings from the backend, no
                        per-factor measurement/citation to build a
                        FindingCard from; kept as a clean two-column list. */}
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-goldStrong mb-2">
                          ✓ {t('eventForecast.positiveFactors')}
                        </h4>
                        <ul className="space-y-1">
                          {forecastResult.positive_factors.map((factor: string, i: number) => (
                            <li key={i} className="text-inkMuted text-sm">
                              {factor}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-danger mb-2">
                          ⚠ {t('eventForecast.riskFactors')}
                        </h4>
                        <ul className="space-y-1">
                          {forecastResult.risk_factors.map((factor: string, i: number) => (
                            <li key={i} className="text-inkMuted text-sm">
                              {factor}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Transits — fetched but previously unrendered;
                        the one part of this response with real
                        measurement (orb, exact date) to back a
                        FindingCard. */}
                    {forecastResult.transits && forecastResult.transits.length > 0 && (
                      <div className="mb-4">
                        <h4 className="font-mono text-[0.68rem] uppercase tracking-widest text-inkFaint mb-3">
                          {locale === 'ru' ? 'Активные транзиты' : 'Active transits'}
                        </h4>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          {forecastResult.transits.slice(0, 4).map((transit, i) => (
                            <FindingCard key={i} {...transitCardProps(transit)} />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommendations */}
                    {forecastResult.recommendations && forecastResult.recommendations.length > 0 && (
                      <div className="mb-4">
                        <h4 className="font-display font-semibold text-ink mb-2">
                          💡 {t('eventForecast.recommendations')}
                        </h4>
                        <ul className="space-y-1">
                          {forecastResult.recommendations.map((rec: string, i: number) => (
                            <li key={i} className="text-inkMuted text-sm flex items-start gap-2">
                              <span className="text-gold">—</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Lunar info */}
                    {forecastResult.lunar_phase && (
                      <div className="mb-4 rounded-md border border-border bg-bgDeep px-3 py-2 font-mono text-xs text-inkMuted">
                        ☽ {forecastResult.lunar_phase}
                        {' · '}{locale === 'ru' ? `день ${forecastResult.lunar_day}` : `day ${forecastResult.lunar_day}`}
                        {forecastResult.retrograde_planets && forecastResult.retrograde_planets.length > 0 && (
                          <span className="text-goldStrong">
                            {' · ℞ '}{forecastResult.retrograde_planets.join(', ')}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Alternative dates */}
                    {forecastResult.alternative_dates && forecastResult.alternative_dates.length > 0 && (
                      <div>
                        <h4 className="font-display font-semibold text-ink mb-2">
                          📅 {t('eventForecast.alternativeDates')}
                        </h4>
                        <div className="flex gap-2 flex-wrap">
                          {forecastResult.alternative_dates.map((date: string) => (
                            <span
                              key={date}
                              className="px-3 py-1 rounded-full border border-border bg-surface font-mono text-xs text-inkMuted"
                            >
                              {date}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Back link */}
          <div className="text-center mt-8">
            <Link
              href={`/${locale}`}
              className="text-inkMuted hover:text-gold transition-colors"
            >
              ← {locale === 'ru' ? 'На главную' : 'Back to Home'}
            </Link>
          </div>
        </div>
      </div>

      {/* Loading Modal - blocks all UI during calculations */}
      <LoadingModal
        isOpen={isCalculating}
        message={locale === 'ru' ? 'Рассчитываем...' : 'Calculating...'}
      />
    </main>
  );
}
