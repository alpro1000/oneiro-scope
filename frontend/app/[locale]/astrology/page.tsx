'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';

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
  const [natalResult, setNatalResult] = useState<any>(null);

  // Event forecast form
  const [eventDate, setEventDate] = useState('');
  const [eventType, setEventType] = useState('travel');
  const [eventLocation, setEventLocation] = useState('');
  const [forecastResult, setForecastResult] = useState<any>(null);

  // Horoscope
  const [horoscopePeriod, setHoroscopePeriod] = useState('daily');
  const [horoscopeResult, setHoroscopeResult] = useState<any>(null);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'natalChart', label: t('tabs.natalChart') },
    { id: 'horoscope', label: t('tabs.horoscope') },
    { id: 'eventForecast', label: t('tabs.eventForecast') },
  ];

  const eventTypes = [
    { value: 'travel', label: locale === 'ru' ? 'Путешествие' : 'Travel' },
    { value: 'wedding', label: locale === 'ru' ? 'Свадьба' : 'Wedding' },
    { value: 'business', label: locale === 'ru' ? 'Бизнес-сделка' : 'Business Deal' },
    { value: 'interview', label: locale === 'ru' ? 'Собеседование' : 'Interview' },
    { value: 'surgery', label: locale === 'ru' ? 'Операция' : 'Surgery' },
    { value: 'moving', label: locale === 'ru' ? 'Переезд' : 'Moving' },
    { value: 'contract', label: locale === 'ru' ? 'Подписание контракта' : 'Contract Signing' },
    { value: 'exam', label: locale === 'ru' ? 'Экзамен' : 'Exam' },
    { value: 'date', label: locale === 'ru' ? 'Свидание' : 'Date' },
  ];

  const handleCalculateNatalChart = async () => {
    if (!birthDate || !birthPlace) return;

    setIsCalculating(true);

    // TODO: Call actual API
    await new Promise((resolve) => setTimeout(resolve, 2000));

    setNatalResult({
      sunSign: locale === 'ru' ? 'Телец' : 'Taurus',
      moonSign: locale === 'ru' ? 'Рак' : 'Cancer',
      ascendant: birthTime ? (locale === 'ru' ? 'Скорпион' : 'Scorpio') : null,
      interpretation:
        locale === 'ru'
          ? 'Ваше Солнце в Тельце придаёт вам стабильность и практичность. Луна в Раке усиливает эмоциональную чувствительность и связь с семьёй.'
          : 'Your Sun in Taurus gives you stability and practicality. Moon in Cancer enhances emotional sensitivity and family connection.',
    });

    setIsCalculating(false);
  };

  const handleGetHoroscope = async () => {
    setIsCalculating(true);

    await new Promise((resolve) => setTimeout(resolve, 1500));

    setHoroscopeResult({
      summary:
        locale === 'ru'
          ? 'Сегодня благоприятный день для начала новых проектов. Луна в растущей фазе усиливает вашу энергию.'
          : 'Today is a favorable day for starting new projects. The waxing Moon enhances your energy.',
      recommendations: [
        locale === 'ru' ? 'Планируйте важные встречи на первую половину дня' : 'Schedule important meetings for the morning',
        locale === 'ru' ? 'Избегайте финансовых рисков' : 'Avoid financial risks',
        locale === 'ru' ? 'Уделите время творчеству' : 'Dedicate time to creativity',
      ],
    });

    setIsCalculating(false);
  };

  const handleGetForecast = async () => {
    if (!eventDate) return;

    setIsCalculating(true);

    await new Promise((resolve) => setTimeout(resolve, 2000));

    setForecastResult({
      favorability: 75,
      level: locale === 'ru' ? 'Хорошо' : 'Good',
      positiveFactors: [
        locale === 'ru' ? 'Юпитер в тригоне с Солнцем' : 'Jupiter trine Sun',
        locale === 'ru' ? 'Растущая Луна' : 'Waxing Moon',
      ],
      riskFactors: [
        locale === 'ru' ? 'Меркурий ретроградный — проверяйте документы' : 'Mercury retrograde — check documents',
      ],
      recommendations: [
        locale === 'ru' ? 'Начните подготовку заранее' : 'Start preparation early',
        locale === 'ru' ? 'Имейте запасной план' : 'Have a backup plan',
      ],
      alternativeDates: ['2024-12-28', '2024-12-30'],
    });

    setIsCalculating(false);
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
                        <p className="text-white font-medium">{natalResult.sunSign}</p>
                      </div>
                      <div>
                        <span className="text-amber-400 text-sm">☽ {locale === 'ru' ? 'Луна' : 'Moon'}</span>
                        <p className="text-white font-medium">{natalResult.moonSign}</p>
                      </div>
                      {natalResult.ascendant && (
                        <div>
                          <span className="text-amber-400 text-sm">↑ {locale === 'ru' ? 'Асцендент' : 'Ascendant'}</span>
                          <p className="text-white font-medium">{natalResult.ascendant}</p>
                        </div>
                      )}
                    </div>
                    <p className="text-slate-300">{natalResult.interpretation}</p>
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
                  {['daily', 'weekly', 'monthly', 'yearly'].map((period) => (
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

                {horoscopeResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 p-4 bg-gradient-to-br from-amber-900/30 to-orange-900/30 border border-amber-500/30 rounded-xl"
                  >
                    <p className="text-slate-300 mb-4">{horoscopeResult.summary}</p>
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
                      {eventTypes.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
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
                        {forecastResult.favorability}%
                      </div>
                      <div className="text-slate-300">{forecastResult.level}</div>

                      {/* Progress bar */}
                      <div className="w-full h-2 bg-slate-700 rounded-full mt-3 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${forecastResult.favorability}%` }}
                          className={`h-full rounded-full ${
                            forecastResult.favorability >= 70
                              ? 'bg-green-500'
                              : forecastResult.favorability >= 40
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
                          {forecastResult.positiveFactors.map((factor: string, i: number) => (
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
                          {forecastResult.riskFactors.map((factor: string, i: number) => (
                            <li key={i} className="text-slate-300 text-sm">
                              {factor}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Recommendations */}
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

                    {/* Alternative dates */}
                    {forecastResult.alternativeDates && forecastResult.alternativeDates.length > 0 && (
                      <div>
                        <h4 className="text-white font-medium mb-2">
                          📅 {t('eventForecast.alternativeDates')}
                        </h4>
                        <div className="flex gap-2">
                          {forecastResult.alternativeDates.map((date: string) => (
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
