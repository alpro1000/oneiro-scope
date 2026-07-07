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
    <main className="oneiro-grid-bg min-h-screen bg-bg">
      {/* Site-wide nav/theme/language now come from the shared Header
          in the root layout — this page no longer duplicates it. */}

      {/* Hero Section */}
      <section className="pt-12 pb-12 px-4">
        <div className="container mx-auto text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="font-display text-4xl font-semibold text-ink mb-6 md:text-5xl lg:text-6xl"
          >
            {t('title')}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-lg md:text-xl text-inkMuted max-w-2xl mx-auto mb-12"
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
            className="rounded-2xl border border-border bg-surface p-8 text-center"
          >
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center text-4xl">
              🎤
            </div>

            <h3 className="font-display text-2xl font-semibold text-ink mb-3">
              {t('voiceInput.title')}
            </h3>

            <p className="text-inkMuted mb-6 max-w-md mx-auto">
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
              <div className="rounded-2xl border border-border bg-surface/60 p-6 transition-colors hover:bg-surface cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="text-3xl">📅</span>
                    <div>
                      <h4 className="font-display font-semibold text-ink">{t('lunarCalendar.title')}</h4>
                      <p className="text-inkMuted text-sm">{t('lunarCalendar.subtitle')}</p>
                    </div>
                  </div>
                  <span className="text-inkFaint">→</span>
                </div>
              </div>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4">
        <div className="container mx-auto text-center">
          <p className="text-inkMuted text-sm">
            {t('footer.disclaimer')}
          </p>
          <p className="text-inkFaint text-xs mt-4">
            © 2024 OneiroScope. {t('footer.rights')}
          </p>
        </div>
      </footer>
    </main>
  );
}
