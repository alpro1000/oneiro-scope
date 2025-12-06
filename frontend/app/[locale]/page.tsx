'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useParams } from 'next/navigation';

export default function HomePage() {
  const t = useTranslations('HomePage');
  const params = useParams();
  const locale = params.locale as string;

  const services = [
    {
      id: 'dreams',
      icon: '🌙',
      href: `/${locale}/dreams`,
      gradient: 'from-indigo-500 to-purple-600',
    },
    {
      id: 'astrology',
      icon: '⭐',
      href: `/${locale}/astrology`,
      gradient: 'from-amber-500 to-orange-600',
    },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href={`/${locale}`} className="flex items-center gap-2">
            <span className="text-2xl">☽</span>
            <span className="text-xl font-semibold text-white">OneiroScope</span>
          </Link>

          {/* Language Switcher */}
          <div className="flex gap-2">
            <Link
              href="/en"
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                locale === 'en'
                  ? 'bg-amber-500/20 text-amber-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              EN
            </Link>
            <Link
              href="/ru"
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

      {/* Hero Section */}
      <section className="pt-24 pb-12 px-4">
        <div className="container mx-auto text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6"
          >
            {t('title')}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-lg md:text-xl text-slate-300 max-w-2xl mx-auto mb-12"
          >
            {t('subtitle')}
          </motion.p>
        </div>
      </section>

      {/* Services Grid */}
      <section className="px-4 pb-12">
        <div className="container mx-auto max-w-4xl">
          <div className="grid md:grid-cols-2 gap-6">
            {services.map((service, index) => (
              <motion.div
                key={service.id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 + index * 0.1 }}
              >
                <Link href={service.href}>
                  <div
                    className={`
                      relative overflow-hidden rounded-2xl p-8
                      bg-gradient-to-br ${service.gradient}
                      transform transition-all duration-300
                      hover:scale-[1.02] hover:shadow-2xl
                      cursor-pointer group
                    `}
                  >
                    {/* Icon */}
                    <div className="text-6xl mb-6">{service.icon}</div>

                    {/* Title */}
                    <h2 className="text-2xl font-bold text-white mb-3">
                      {t(`services.${service.id}.title`)}
                    </h2>

                    {/* Description */}
                    <p className="text-white/80 mb-6">
                      {t(`services.${service.id}.description`)}
                    </p>

                    {/* Features */}
                    <ul className="space-y-2 mb-6">
                      {[1, 2, 3].map((i) => (
                        <li key={i} className="flex items-center gap-2 text-white/70">
                          <span className="w-1.5 h-1.5 rounded-full bg-white/50" />
                          {t(`services.${service.id}.feature${i}`)}
                        </li>
                      ))}
                    </ul>

                    {/* CTA */}
                    <div className="flex items-center gap-2 text-white font-medium group-hover:gap-3 transition-all">
                      {t('startButton')}
                      <span className="text-xl">→</span>
                    </div>

                    {/* Decorative elements */}
                    <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                    <div className="absolute bottom-0 left-0 w-24 h-24 bg-black/10 rounded-full translate-y-1/2 -translate-x-1/2" />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Voice Input Section */}
      <section className="px-4 pb-12">
        <div className="container mx-auto max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-8 text-center"
          >
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center text-4xl">
              🎤
            </div>

            <h3 className="text-2xl font-bold text-white mb-3">
              {t('voiceInput.title')}
            </h3>

            <p className="text-slate-300 mb-6 max-w-md mx-auto">
              {t('voiceInput.description')}
            </p>

            <button
              className="
                px-8 py-4 rounded-full
                bg-gradient-to-r from-rose-500 to-pink-600
                text-white font-medium
                transform transition-all duration-300
                hover:scale-105 hover:shadow-lg hover:shadow-rose-500/25
                active:scale-95
              "
            >
              {t('voiceInput.button')}
            </button>
          </motion.div>
        </div>
      </section>

      {/* Lunar Widget Preview */}
      <section className="px-4 pb-12">
        <div className="container mx-auto max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
          >
            <Link href={`/${locale}/calendar`}>
              <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6 hover:bg-slate-800/50 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="text-3xl">📅</span>
                    <div>
                      <h4 className="text-white font-medium">{t('lunarCalendar.title')}</h4>
                      <p className="text-slate-400 text-sm">{t('lunarCalendar.subtitle')}</p>
                    </div>
                  </div>
                  <span className="text-slate-400">→</span>
                </div>
              </div>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 px-4">
        <div className="container mx-auto text-center">
          <p className="text-slate-500 text-sm">
            {t('footer.disclaimer')}
          </p>
          <p className="text-slate-600 text-xs mt-4">
            © 2024 OneiroScope. {t('footer.rights')}
          </p>
        </div>
      </footer>
    </main>
  );
}
