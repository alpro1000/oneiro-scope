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
} from '../../../lib/astrology-client';

type Tab = 'natalChart' | 'horoscope' | 'eventForecast';

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
    <main className="min-h-screen bg-gradient-to-b from-slate-900 via-amber-950/20 to-slate-900">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href={`/${locale}`} className="flex items-center gap-2">
            <span className="text-2xl">☽</span>
            <span className="text-xl font-semibold text-white">OneiroScope</span>
          </Link>

          <div className="flex gap-2">
            <Link
              href={`/en/astrology`}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                locale === 'en'
                  ? 'bg-amber-500/20 text-amber-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              EN
            </Link>
            <Link
              href={`/ru/astrology`}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                locale === 'ru'
                  ? 'bg-amber-500/20 text-amber-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              RU
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="pt-24 pb-12 px-4">
        <div className="container mx-auto max-w-3xl">
          {/* Title */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
              {t('title')}
            </h1>
            <p className="text-slate-300">{t('subtitle')}</p>
          </motion.div>

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex justify-center gap-2 mb-8"
          >
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium
                  transition-all duration-300
                  ${
                    activeTab === tab.id
                      ? 'bg-amber-500 text-white'
                      : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
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
                className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6"
              >
                <h2 className="text-xl font-semibold text-white mb-6">
                  {t('natalChart.title')}
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-slate-300 text-sm mb-2">
                      {t('natalChart.birthDate')} *
                    </label>
                    <input
                      type="date"
                      value={birthDate}
                      onChange={(e) => setBirthDate(e.target.value)}
                      className="w-full p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-300 text-sm mb-2">
                      {t('natalChart.birthTime')}
                    </label>
                    <input
                      type="time"
                      value={birthTime}
                      onChange={(e) => setBirthTime(e.target.value)}
                      className="w-full p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                    <p className="text-slate-500 text-xs mt-1">
                      {t('natalChart.unknownTime')}
                    </p>
                  </div>

                  <div>
                    <label className="block text-slate-300 text-sm mb-2">
                      {t('natalChart.birthPlace')} *
                    </label>
                    <input
                      type="text"
                      value={birthPlace}
                      onChange={(e) => setBirthPlace(e.target.value)}
                      placeholder={locale === 'ru' ? 'Москва, Россия' : 'Moscow, Russia'}
                      className="w-full p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>

                  <button
                    onClick={handleCalculateNatalChart}
                    disabled={!birthDate || !birthPlace || isCalculating}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 text-white font-medium transition-all hover:from-amber-600 hover:to-orange-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {isCalculating ? (
                      <motion.div
                        className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
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
                    className="mt-6 p-4 bg-red-900/30 border border-red-500/30 rounded-xl"
                  >
                    <p className="text-red-300">{natalError}</p>
                  </motion.div>
                )}

                {/* Result */}
                {natalResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-gradient-to-br from-amber-900/30 to-orange-900/30 border border-amber-500/30 rounded-xl"
                  >
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <span className="text-amber-400 text-sm">☉ {locale === 'ru' ? 'Солнце' : 'Sun'}</span>
                        <p className="text-white font-medium">{natalResult.sun_sign}</p>
                      </div>
                      <div>
                        <span className="text-amber-400 text-sm">☽ {locale === 'ru' ? 'Луна' : 'Moon'}</span>
                        <p className="text-white font-medium">{natalResult.moon_sign}</p>
                      </div>
                      {natalResult.ascendant && (
                        <div>
                          <span className="text-amber-400 text-sm">↑ {locale === 'ru' ? 'Асцендент' : 'Ascendant'}</span>
                          <p className="text-white font-medium">{natalResult.ascendant}</p>
                        </div>
                      )}
                    </div>

                    {/* Planet positions */}
                    {natalResult.planets && natalResult.planets.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-amber-400 font-medium mb-2">
                          {locale === 'ru' ? 'Планеты' : 'Planets'}
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                          {natalResult.planets.slice(0, 10).map((planet) => (
                            <div key={planet.name} className="flex items-center gap-1 text-slate-300">
                              <span>{planet.symbol}</span>
                              <span>{planet.name}</span>
                              <span className="text-amber-400">{planet.sign}</span>
                              {planet.retrograde && <span className="text-red-400">℞</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {natalResult.interpretation && (
                      <p className="text-slate-300">{natalResult.interpretation}</p>
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
                className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6"
              >
                <h2 className="text-xl font-semibold text-white mb-6">
                  {t('horoscope.title')}
                </h2>

                <div className="flex gap-2 mb-6">
                  {horoscopePeriods.map((period) => (
                    <button
                      key={period}
                      onClick={() => setHoroscopePeriod(period)}
                      className={`px-4 py-2 rounded-lg text-sm transition-all ${
                        horoscopePeriod === period
                          ? 'bg-amber-500 text-white'
                          : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                      }`}
                    >
                      {t(`horoscope.${period}`)}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleGetHoroscope}
                  disabled={isCalculating}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isCalculating ? (
                    <motion.div
                      className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
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
                    className="mt-6 p-4 bg-red-900/30 border border-red-500/30 rounded-xl"
                  >
                    <p className="text-red-300">{horoscopeError}</p>
                  </motion.div>
                )}

                {horoscopeResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-gradient-to-br from-amber-900/30 to-orange-900/30 border border-amber-500/30 rounded-xl"
                  >
                    {/* Lunar info */}
                    <div className="flex items-center gap-4 mb-4 text-sm text-slate-400">
                      <span>☽ {horoscopeResult.lunar_phase}</span>
                      <span>{locale === 'ru' ? `День ${horoscopeResult.lunar_day}` : `Day ${horoscopeResult.lunar_day}`}</span>
                      {horoscopeResult.retrograde_planets.length > 0 && (
                        <span className="text-amber-400">
                          ℞ {horoscopeResult.retrograde_planets.join(', ')}
                        </span>
                      )}
                    </div>

                    <p className="text-slate-300 mb-4">{horoscopeResult.summary}</p>

                    {horoscopeResult.recommendations && horoscopeResult.recommendations.length > 0 && (
                      <>
                        <h4 className="text-amber-400 font-medium mb-2">
                          {t('eventForecast.recommendations')}:
                        </h4>
                        <ul className="space-y-2">
                          {horoscopeResult.recommendations.map((rec: string, i: number) => (
                            <li key={i} className="text-slate-300 flex items-start gap-2">
                              <span className="text-amber-400">•</span>
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
                className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6"
              >
                <h2 className="text-xl font-semibold text-white mb-6">
                  {t('eventForecast.title')}
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-slate-300 text-sm mb-2">
                      {t('eventForecast.eventDate')} *
                    </label>
                    <input
                      type="date"
                      value={eventDate}
                      onChange={(e) => setEventDate(e.target.value)}
                      className="w-full p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-300 text-sm mb-2">
                      {t('eventForecast.eventType')}
                    </label>
                    <select
                      value={eventType}
                      onChange={(e) => setEventType(e.target.value)}
                      className="w-full p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                    >
                      {displayEventTypes.map((type) => (
                        <option key={type.value} value={type.value}>
                          {locale === 'ru' ? type.label_ru : type.label_en}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-300 text-sm mb-2">
                      {t('eventForecast.eventLocation')}
                    </label>
                    <input
                      type="text"
                      value={eventLocation}
                      onChange={(e) => setEventLocation(e.target.value)}
                      placeholder={locale === 'ru' ? 'Париж, Франция' : 'Paris, France'}
                      className="w-full p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>

                  <button
                    onClick={handleGetForecast}
                    disabled={!eventDate || isCalculating}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isCalculating ? (
                      <motion.div
                        className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
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
                    className="mt-6 p-4 bg-red-900/30 border border-red-500/30 rounded-xl"
                  >
                    <p className="text-red-300">{forecastError}</p>
                  </motion.div>
                )}

                {/* Forecast Result */}
                {forecastResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-gradient-to-br from-amber-900/30 to-orange-900/30 border border-amber-500/30 rounded-xl"
                  >
                    {/* Favorability Score */}
                    <div className="text-center mb-6">
                      <div className="text-4xl font-bold text-amber-400 mb-1">
                        {forecastResult.favorability_score}%
                      </div>
                      <div className="text-slate-300">{forecastResult.level}</div>

                      {/* Progress bar */}
                      <div className="w-full h-2 bg-slate-700 rounded-full mt-3 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${forecastResult.favorability_score}%` }}
                          className={`h-full rounded-full ${
                            forecastResult.favorability_score >= 70
                              ? 'bg-green-500'
                              : forecastResult.favorability_score >= 40
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                          }`}
                        />
                      </div>
                    </div>

                    {/* Factors */}
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <h4 className="text-green-400 font-medium mb-2">
                          ✓ {t('eventForecast.positiveFactors')}
                        </h4>
                        <ul className="space-y-1">
                          {forecastResult.positive_factors.map((factor: string, i: number) => (
                            <li key={i} className="text-slate-300 text-sm">
                              {factor}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="text-amber-400 font-medium mb-2">
                          ⚠ {t('eventForecast.riskFactors')}
                        </h4>
                        <ul className="space-y-1">
                          {forecastResult.risk_factors.map((factor: string, i: number) => (
                            <li key={i} className="text-slate-300 text-sm">
                              {factor}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Recommendations */}
                    {forecastResult.recommendations && forecastResult.recommendations.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-white font-medium mb-2">
                          💡 {t('eventForecast.recommendations')}
                        </h4>
                        <ul className="space-y-1">
                          {forecastResult.recommendations.map((rec: string, i: number) => (
                            <li key={i} className="text-slate-300 text-sm">
                              • {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Interpretation */}
                    {forecastResult.interpretation && (
                      <p className="text-slate-300 mb-4 text-sm italic">
                        {forecastResult.interpretation}
                      </p>
                    )}

                    {/* Alternative dates */}
                    {forecastResult.alternative_dates && forecastResult.alternative_dates.length > 0 && (
                      <div>
                        <h4 className="text-white font-medium mb-2">
                          📅 {t('eventForecast.alternativeDates')}
                        </h4>
                        <div className="flex gap-2 flex-wrap">
                          {forecastResult.alternative_dates.map((date: string) => (
                            <span
                              key={date}
                              className="px-3 py-1 bg-slate-700 rounded-lg text-slate-300 text-sm"
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
              className="text-slate-400 hover:text-white transition-colors"
            >
              ← {locale === 'ru' ? 'На главную' : 'Back to Home'}
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
