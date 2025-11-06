import type {Metadata} from 'next';
import '../styles/tokens.css';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: 'ONEIROSCOP Lunar Calendar',
  description: 'Immersive lunar calendar experience for ONEIROSCOP-LUNAR.'
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
