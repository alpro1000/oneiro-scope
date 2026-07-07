'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import VoiceInput from '../../../components/VoiceInput';
import LoadingModal from '../../../components/LoadingModal';
import ConfidenceBadge from '../../../components/ConfidenceBadge';
import FindingCard from '../../../components/FindingCard';
import {
  analyzeDream,
  type DreamAnalysisResponse,
  type DreamSymbol,
} from '../../../lib/dreams-client';

// Hall/Van de Castle category labels (matches backend/api/v1/dreams.py
// /categories endpoint) — used only to caption a symbol's measurement
// line, not to invent new content.
const CATEGORY_LABEL: Record<string, {ru: string; en: string}> = {
  characters: {ru: 'персонажи', en: 'characters'},
  social_interactions: {ru: 'взаимодействия', en: 'social interactions'},
  activities: {ru: 'действия', en: 'activities'},
  striving: {ru: 'цели', en: 'striving'},
  misfortunes: {ru: 'неудачи', en: 'misfortunes'},
  good_fortunes: {ru: 'удачи', en: 'good fortunes'},
  emotions: {ru: 'эмоции', en: 'emotions'},
  settings: {ru: 'место действия', en: 'settings'},
  objects: {ru: 'предметы', en: 'objects'},
  descriptive_elements: {ru: 'детали', en: 'descriptive elements'},
};

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

  const symbolCardProps = (symbol: DreamSymbol) => {
    const ru = locale === 'ru';
    const category = CATEGORY_LABEL[symbol.category]?.[ru ? 'ru' : 'en'] || symbol.category;
    return {
      title: symbol.symbol.charAt(0).toUpperCase() + symbol.symbol.slice(1),
      seenLabel: ru ? 'Система увидела' : 'System saw',
      seenText: ru
        ? `категория: ${category} · значимость ${Math.round(symbol.significance * 100)}%`
        : `category: ${category} · significance ${Math.round(symbol.significance * 100)}%`,
      traditionQuote: ru ? symbol.interpretation_ru : symbol.interpretation_en,
      traditionSource: symbol.archetype
        ? (ru
            ? `юнгианская школа толкования снов · архетип: ${symbol.archetype}`
            : `Jungian dream interpretation · archetype: ${symbol.archetype}`)
        : (ru ? 'традиционные сонники' : 'traditional dream dictionaries'),
    };
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

          {/* Input Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-2xl border border-border bg-surface p-6 mb-6"
          >
            {/* Textarea */}
            <textarea
              value={dreamText}
              onChange={(e) => setDreamText(e.target.value)}
              placeholder={t('inputPlaceholder')}
              className="
                w-full h-48 p-4
                bg-bgDeep border border-border
                rounded-xl text-ink placeholder-inkFaint
                focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent
                resize-none
              "
            />

            {/* Dream date (optional) */}
            <div className="mt-4">
              <label className="block text-inkMuted text-sm mb-2">
                {locale === 'ru' ? 'Дата сна (опционально)' : 'Dream date (optional)'}
              </label>
              <input
                type="date"
                value={dreamDate}
                onChange={(e) => setDreamDate(e.target.value)}
                className="w-full md:w-auto p-3 bg-bgDeep border border-border rounded-lg text-ink focus:outline-none focus:ring-2 focus:ring-gold"
              />
              <p className="text-inkFaint text-xs mt-1">
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
                  px-8 py-3 rounded-full
                  bg-gold text-bgDeep font-semibold
                  transition-colors duration-200
                  hover:bg-goldStrong
                  disabled:opacity-50 disabled:cursor-not-allowed
                  flex items-center gap-2
                "
              >
                {isAnalyzing ? (
                  <>
                    <motion.div
                      className="w-5 h-5 border-2 border-bgDeep border-t-transparent rounded-full"
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
            <p className="text-inkFaint text-sm mt-4 text-center">
              {t('methodology')}
            </p>
          </motion.div>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-danger/10 border border-danger/30 rounded-xl"
            >
              <p className="text-danger">{error}</p>
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
              <div className="rounded-2xl border border-border bg-surface p-6">
                <h2 className="font-display text-xl font-semibold text-ink mb-4 flex items-center gap-2">
                  <span>🌙</span>
                  {locale === 'ru' ? 'Краткое резюме' : 'Summary'}
                </h2>
                <p className="text-inkMuted text-lg">{analysis.summary}</p>

                {/* Emotion indicator */}
                <div className="mt-4 flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[0.68rem] uppercase tracking-widest text-inkFaint">
                      {locale === 'ru' ? 'Эмоция' : 'Emotion'}
                    </span>
                    <span className="font-display font-semibold text-goldStrong">
                      {getEmotionLabel(analysis.primary_emotion)}
                    </span>
                  </div>
                  <div className="flex-1 h-2 bg-border rounded-full overflow-hidden max-w-32">
                    <div
                      className="h-full bg-gold rounded-full"
                      style={{ width: `${analysis.emotion_intensity * 100}%` }}
                    />
                  </div>
                </div>

                <div className="mt-4">
                  <ConfidenceBadge
                    score={0.7}
                    source={locale === 'ru' ? 'сопоставление символов · ИИ-интерпретация' : 'symbol matching · AI interpretation'}
                  />
                </div>
              </div>

              {/* Symbols */}
              {analysis.symbols.length > 0 && (
                <div className="findings-section">
                  <h3 className="font-display text-lg font-semibold text-ink mb-4">
                    {locale === 'ru' ? 'Найденные символы' : 'Found Symbols'}
                  </h3>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {analysis.symbols.slice(0, 6).map((symbol, i) => (
                      <FindingCard key={i} {...symbolCardProps(symbol)} />
                    ))}
                  </div>
                </div>
              )}

              {/* Full Interpretation */}
              <div className="rounded-2xl border border-border bg-surface p-6">
                <h3 className="font-display text-lg font-semibold text-ink mb-4">
                  {locale === 'ru' ? 'Полная интерпретация' : 'Full Interpretation'}
                </h3>
                <div className="text-inkMuted space-y-3">
                  {analysis.interpretation.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              </div>

              {/* Themes & Archetypes */}
              {(analysis.themes.length > 0 || analysis.archetypes.length > 0) && (
                <div className="grid md:grid-cols-2 gap-4">
                  {analysis.themes.length > 0 && (
                    <div className="rounded-xl border border-border bg-surface p-4">
                      <h4 className="font-display font-semibold text-ink mb-2">
                        {locale === 'ru' ? 'Темы' : 'Themes'}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {analysis.themes.map((theme, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 rounded-full border border-border bg-surfaceStrong font-mono text-xs text-inkMuted"
                          >
                            {theme}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {analysis.archetypes.length > 0 && (
                    <div className="rounded-xl border border-border bg-surface p-4">
                      <h4 className="font-display font-semibold text-ink mb-2">
                        {locale === 'ru' ? 'Архетипы' : 'Archetypes'}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {analysis.archetypes.map((archetype, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 rounded-full border border-gold font-mono text-xs text-goldStrong capitalize"
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
                <div className="rounded-xl border border-border bg-surface p-4">
                  <h4 className="font-display font-semibold text-ink mb-2 flex items-center gap-2">
                    <span>🌙</span>
                    {locale === 'ru' ? 'Лунный контекст' : 'Lunar Context'}
                  </h4>
                  <div className="mb-2 rounded-md border border-border bg-bgDeep px-3 py-2 font-mono text-xs text-inkMuted">
                    {locale === 'ru'
                      ? `${analysis.lunar_context.lunar_day}-й лунный день`
                      : `Lunar day ${analysis.lunar_context.lunar_day}`}
                    {' · '}{analysis.lunar_context.lunar_phase}
                    {analysis.lunar_context.moon_sign && ` · ${analysis.lunar_context.moon_sign}`}
                  </div>
                  <p className="text-inkMuted text-sm">
                    {locale === 'ru'
                      ? analysis.lunar_context.interpretation_ru
                      : analysis.lunar_context.interpretation_en}
                  </p>
                </div>
              )}

              {/* Recommendations */}
              {analysis.recommendations.length > 0 && (
                <div className="rounded-xl border border-border bg-surface p-4">
                  <h4 className="font-display font-semibold text-ink mb-3">
                    {locale === 'ru' ? 'Рекомендации' : 'Recommendations'}
                  </h4>
                  <ul className="space-y-2">
                    {analysis.recommendations.map((rec, i) => (
                      <li key={i} className="text-inkMuted text-sm flex items-start gap-2">
                        <span className="text-gold">—</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Methodology footer */}
              <p className="text-center text-inkFaint text-xs">
                {analysis.methodology}
              </p>
            </motion.div>
          )}

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

      {/* Loading Modal - blocks all UI during analysis */}
      <LoadingModal
        isOpen={isAnalyzing}
        message={locale === 'ru' ? 'Анализируем сон...' : 'Analyzing dream...'}
      />
    </main>
  );
}
