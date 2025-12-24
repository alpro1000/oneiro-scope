'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import VoiceInput from '../../../components/VoiceInput';
import LoadingModal from '../../../components/LoadingModal';
import {
  analyzeDream,
  type DreamAnalysisResponse,
} from '../../../lib/dreams-client';

export default function DreamsPage() {
  const t = useTranslations('DreamsPage');
  const params = useParams();
  const locale = (params.locale as string) || 'ru';

  const [dreamText, setDreamText] = useState('');
  const [dreamDate, setDreamDate] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<DreamAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVoiceTranscript = (text: string) => {
    setDreamText((prev) => (prev ? `${prev} ${text}` : text));
  };

  const handleAnalyze = async () => {
    if (!dreamText.trim()) return;

    setIsAnalyzing(true);
    setError(null);
    setAnalysis(null);

    try {
      const result = await analyzeDream({
        dream_text: dreamText,
        dream_date: dreamDate || undefined,
        locale,
      });
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze dream');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getEmotionLabel = (emotion: string): string => {
    const emotions: Record<string, { ru: string; en: string }> = {
      happiness: { ru: 'Радость', en: 'Happiness' },
      sadness: { ru: 'Печаль', en: 'Sadness' },
      anger: { ru: 'Гнев', en: 'Anger' },
      apprehension: { ru: 'Тревога', en: 'Apprehension' },
      confusion: { ru: 'Смятение', en: 'Confusion' },
      neutral: { ru: 'Нейтральное', en: 'Neutral' },
    };
    return emotions[emotion]?.[locale as 'ru' | 'en'] || emotion;
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-900 via-indigo-950 to-slate-900">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href={`/${locale}`} className="flex items-center gap-2">
            <span className="text-2xl">☽</span>
            <span className="text-xl font-semibold text-white">OneiroScope</span>
          </Link>

          <div className="flex gap-2">
            <Link
              href={`/en/dreams`}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                locale === 'en'
                  ? 'bg-indigo-500/20 text-indigo-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              EN
            </Link>
            <Link
              href={`/ru/dreams`}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                locale === 'ru'
                  ? 'bg-indigo-500/20 text-indigo-400'
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

          {/* Input Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 mb-6"
          >
            {/* Textarea */}
            <textarea
              value={dreamText}
              onChange={(e) => setDreamText(e.target.value)}
              placeholder={t('inputPlaceholder')}
              className="
                w-full h-48 p-4
                bg-slate-900/50 border border-slate-700
                rounded-xl text-white placeholder-slate-500
                focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                resize-none
              "
            />

            {/* Dream date (optional) */}
            <div className="mt-4">
              <label className="block text-slate-400 text-sm mb-2">
                {locale === 'ru' ? 'Дата сна (опционально)' : 'Dream date (optional)'}
              </label>
              <input
                type="date"
                value={dreamDate}
                onChange={(e) => setDreamDate(e.target.value)}
                className="w-full md:w-auto p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-slate-500 text-xs mt-1">
                {locale === 'ru'
                  ? 'Указание даты добавит лунный контекст к анализу'
                  : 'Adding date will include lunar context in analysis'}
              </p>
            </div>

            {/* Voice Input & Analyze Button */}
            <div className="flex items-center justify-between mt-4">
              <VoiceInput
                onTranscript={handleVoiceTranscript}
                language={locale as 'ru' | 'en'}
                size="md"
              />

              <button
                onClick={handleAnalyze}
                disabled={!dreamText.trim() || isAnalyzing}
                className="
                  px-8 py-3 rounded-xl
                  bg-gradient-to-r from-indigo-500 to-purple-600
                  text-white font-medium
                  transition-all duration-300
                  hover:from-indigo-600 hover:to-purple-700
                  disabled:opacity-50 disabled:cursor-not-allowed
                  flex items-center gap-2
                "
              >
                {isAnalyzing ? (
                  <>
                    <motion.div
                      className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    {locale === 'ru' ? 'Анализирую...' : 'Analyzing...'}
                  </>
                ) : (
                  <>
                    <span>✨</span>
                    {t('analyzeButton')}
                  </>
                )}
              </button>
            </div>

            {/* Methodology note */}
            <p className="text-slate-500 text-sm mt-4 text-center">
              {t('methodology')}
            </p>
          </motion.div>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-red-900/30 border border-red-500/30 rounded-xl"
            >
              <p className="text-red-300">{error}</p>
            </motion.div>
          )}

          {/* Analysis Result */}
          {analysis && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Summary Card */}
              <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 rounded-2xl p-6">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <span>🌙</span>
                  {locale === 'ru' ? 'Краткое резюме' : 'Summary'}
                </h2>
                <p className="text-slate-300 text-lg">{analysis.summary}</p>

                {/* Emotion indicator */}
                <div className="mt-4 flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 text-sm">
                      {locale === 'ru' ? 'Эмоция:' : 'Emotion:'}
                    </span>
                    <span className="text-indigo-400 font-medium">
                      {getEmotionLabel(analysis.primary_emotion)}
                    </span>
                  </div>
                  <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden max-w-32">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${analysis.emotion_intensity * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Symbols */}
              {analysis.symbols.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">
                    {locale === 'ru' ? 'Найденные символы' : 'Found Symbols'}
                  </h3>
                  <div className="space-y-3">
                    {analysis.symbols.slice(0, 5).map((symbol, i) => (
                      <div key={i} className="p-3 bg-slate-900/50 rounded-lg">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-indigo-400 font-medium capitalize">
                            {symbol.symbol}
                          </span>
                          {symbol.archetype && (
                            <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
                              {symbol.archetype}
                            </span>
                          )}
                        </div>
                        <p className="text-slate-300 text-sm">
                          {locale === 'ru' ? symbol.interpretation_ru : symbol.interpretation_en}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Full Interpretation */}
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4">
                  {locale === 'ru' ? 'Полная интерпретация' : 'Full Interpretation'}
                </h3>
                <div className="text-slate-300 space-y-3">
                  {analysis.interpretation.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              </div>

              {/* Themes & Archetypes */}
              {(analysis.themes.length > 0 || analysis.archetypes.length > 0) && (
                <div className="grid md:grid-cols-2 gap-4">
                  {analysis.themes.length > 0 && (
                    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                      <h4 className="text-white font-medium mb-2">
                        {locale === 'ru' ? 'Темы' : 'Themes'}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {analysis.themes.map((theme, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-indigo-900/50 text-indigo-300 rounded-full text-sm"
                          >
                            {theme}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {analysis.archetypes.length > 0 && (
                    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                      <h4 className="text-white font-medium mb-2">
                        {locale === 'ru' ? 'Архетипы' : 'Archetypes'}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {analysis.archetypes.map((archetype, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-purple-900/50 text-purple-300 rounded-full text-sm capitalize"
                          >
                            {archetype.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Lunar Context */}
              {analysis.lunar_context && (
                <div className="bg-gradient-to-r from-indigo-900/30 to-slate-800/50 border border-indigo-500/20 rounded-xl p-4">
                  <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                    <span>🌙</span>
                    {locale === 'ru' ? 'Лунный контекст' : 'Lunar Context'}
                  </h4>
                  <div className="flex items-center gap-4 text-sm text-slate-400 mb-2">
                    <span>
                      {locale === 'ru'
                        ? `${analysis.lunar_context.lunar_day}-й лунный день`
                        : `Lunar day ${analysis.lunar_context.lunar_day}`}
                    </span>
                    <span>{analysis.lunar_context.lunar_phase}</span>
                    {analysis.lunar_context.moon_sign && (
                      <span>{analysis.lunar_context.moon_sign}</span>
                    )}
                  </div>
                  <p className="text-slate-300 text-sm">
                    {locale === 'ru'
                      ? analysis.lunar_context.interpretation_ru
                      : analysis.lunar_context.interpretation_en}
                  </p>
                </div>
              )}

              {/* Recommendations */}
              {analysis.recommendations.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                  <h4 className="text-white font-medium mb-3">
                    {locale === 'ru' ? 'Рекомендации' : 'Recommendations'}
                  </h4>
                  <ul className="space-y-2">
                    {analysis.recommendations.map((rec, i) => (
                      <li key={i} className="text-slate-300 text-sm flex items-start gap-2">
                        <span className="text-indigo-400">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Methodology footer */}
              <p className="text-center text-slate-500 text-xs">
                {analysis.methodology}
              </p>
            </motion.div>
          )}

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

      {/* Loading Modal - blocks all UI during analysis */}
      <LoadingModal
        isOpen={isAnalyzing}
        message={locale === 'ru' ? 'Анализируем сон...' : 'Analyzing dream...'}
      />
    </main>
  );
}
