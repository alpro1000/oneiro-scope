import type {Config} from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    './__tests__/**/*.{ts,tsx}',
    './stories/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        surfaceStrong: 'var(--surface-strong)',
        gold: 'var(--gold)',
        goldSoft: 'var(--gold-soft)',
        ink: 'var(--ink)',
        inkMuted: 'var(--ink-muted)',
        accent: 'var(--accent)',
        danger: 'var(--danger)'
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'Inter', 'sans-serif']
      },
      boxShadow: {
        gold: 'var(--shadow-gold)'
      },
      borderRadius: {
        lg: 'var(--radius-lg)',
        md: 'var(--radius-md)',
        sm: 'var(--radius-sm)'
      },
      transitionTimingFunction: {
        lunar: 'ease-in-out'
      },
      transitionDuration: {
        lunar: '300ms'
      }
    }
  },
  plugins: []
};

export default config;
