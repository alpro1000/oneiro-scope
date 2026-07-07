import {NextIntlClientProvider} from 'next-intl';
import {ReactNode} from 'react';
import {notFound} from 'next/navigation';
import {Fraunces, IBM_Plex_Mono, Inter} from 'next/font/google';
import Header from '../../components/Header';
import ThemeInit from '../../components/ThemeInit';

import '../../styles/tokens.css';
import '../../styles/globals.css';

export const dynamic = 'force-dynamic';

// Self-hosted via next/font (no external request, no FOUC). Fraunces
// has no Cyrillic glyphs on Google Fonts, so RU headings fall back to
// the CSS chain's next serif (Georgia) — intentional, see tokens.css.
const fraunces = Fraunces({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  variable: '--font-display-face',
  display: 'swap',
});
const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-body',
  display: 'swap',
});
const plexMono = IBM_Plex_Mono({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600'],
  variable: '--font-mono-face',
  display: 'swap',
});

export default async function LocaleLayout({
  children,
  params
}: {
  children: ReactNode;
  params: {locale: string};
}) {
  const {locale} = params;

  let messages;
  try {
    messages = (await import(`../../messages/${locale}.json`)).default;
  } catch (error) {
    notFound();
  }

  return (
    <html lang={locale} className={`${fraunces.variable} ${inter.variable} ${plexMono.variable}`} suppressHydrationWarning>
      <body className="bg-bg text-ink antialiased">
        <ThemeInit />
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Header />
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
