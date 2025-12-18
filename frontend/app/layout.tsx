import type {Metadata} from 'next';
import {ReactNode} from 'react';

export const metadata: Metadata = {
  title: {
    default: 'OneiroScope — Астрология, Сны и Лунный Календарь',
    template: '%s | OneiroScope'
  },
  description: 'Научный подход к астрологии, анализу снов и лунному календарю. Swiss Ephemeris, Hall/Van de Castle методология.',
  icons: {
    icon: [
      {url: '/favicon.svg', type: 'image/svg+xml'},
    ],
  },
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    alternateLocale: ['en_US'],
    siteName: 'OneiroScope',
  }
};

export default function RootLayout({children}: {children: ReactNode}) {
  return children;
}
