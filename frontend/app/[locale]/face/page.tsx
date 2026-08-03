import { useTranslations } from 'next-intl';
import FaceScanner from '../../../components/FaceScanner';

/**
 * Face scanner shell — instrument header + the scanner itself.
 *
 * The gradient/slate shell this replaces was the last of the old palette on
 * this route (it is what still read as "old design" once the global header had
 * already been rebuilt). Layout matches natal/astro/calendar: eyebrow, display
 * heading with a brass accent, then the instrument.
 */
export default function FacePage({
  params,
}: {
  params: { locale: string };
}) {
  const t = useTranslations('FacePage');
  const ru = params.locale === 'ru';

  return (
    <main style={{ padding: 'clamp(14px,2.2vw,30px)', maxWidth: 900, margin: '0 auto' }}>
      <header
        style={{
          paddingBottom: 14,
          marginBottom: 'clamp(12px,1.6vw,20px)',
          borderBottom: '1px solid var(--grat-1)',
        }}
      >
        <span className="eyebrow">{ru ? 'сканер лица · мяньсян' : 'face scanner · mianxiang'}</span>
        <h1 style={{ fontSize: 'clamp(28px,5vw,52px)', margin: '4px 0 0' }}>
          {t('title')}
        </h1>
        <p
          style={{
            color: 'var(--muted)',
            fontSize: 13.5,
            lineHeight: 1.6,
            maxWidth: '58ch',
            marginTop: 12,
          }}
        >
          {t('subtitle')}
        </p>
      </header>

      <FaceScanner locale={params.locale} />
    </main>
  );
}
