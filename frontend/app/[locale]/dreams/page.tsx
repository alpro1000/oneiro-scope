'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import VoiceInput from '@/components/VoiceInput';

export default function DreamsPage() {
  const t = useTranslations('DreamsPage');
  const params = useParams();
  const locale = (params.locale as string) || 'ru';

  const [dreamText, setDreamText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);

  const handleVoiceTranscript = (text: string) => {
    setDreamText((prev) => (prev ? `${prev} ${text}` : text));
  };

  const handleAnalyze = async () => {
    if (!dreamText.trim()) return;

    setIsAnalyzing(true);
    setAnalysis(null);

    // TODO: Call actual API
    // Simulating API call
    await new Promise((resolve) => setTimeout(resolve, 2000));

    setAnalysis(
      locale === 'ru'
        ? `**Анализ вашего сна:**\n\nВаш сон содержит интересные символы, которые могут указывать на текущие жизненные процессы. Согласно методологии Hall/Van de Castle, сновидение относится к категории [категория].\n\n**Ключевые символы:**\n- Символ 1: интерпретация\n- Символ 2: интерпретация\n\n**Лунный контекст:**\nСон был записан в 15-й лунный день (Полнолуние), что усиливает его значимость.`
        : `**Dream Analysis:**\n\nYour dream contains interesting symbols that may indicate current life processes. According to the Hall/Van de Castle methodology, this dream belongs to [category].\n\n**Key Symbols:**\n- Symbol 1: interpretation\n- Symbol 2: interpretation\n\n**Lunar Context:**\nThe dream was recorded on the 15th lunar day (Full Moon), which enhances its significance.`
    );

    setIsAnalyzing(false);
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

          {/* Analysis Result */}
          {analysis && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 rounded-2xl p-6"
            >
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <span>🌙</span>
                {locale === 'ru' ? 'Результат анализа' : 'Analysis Result'}
              </h2>

              <div className="prose prose-invert prose-sm max-w-none">
                {analysis.split('\n').map((line, i) => (
                  <p key={i} className="text-slate-300 mb-2">
                    {line.startsWith('**') ? (
                      <strong className="text-white">
                        {line.replace(/\*\*/g, '')}
                      </strong>
                    ) : line.startsWith('-') ? (
                      <span className="ml-4 block">{line}</span>
                    ) : (
                      line
                    )}
                  </p>
                ))}
              </div>
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
    </main>
  );
}
