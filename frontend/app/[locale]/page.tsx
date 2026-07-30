import Link from 'next/link';

/**
 * Home — the instrument index, screen 0 of the design system.
 *
 * Not a marketing splash: it presents the four working tools as bordered
 * instrument panels (border, never shadow; radius 0 globally) and states the
 * house rule up front — the numbers are computed and reproducible, the meaning
 * is tradition. No framer-motion, no gradient cards, no hardcoded Tailwind
 * palette; a Server Component, so nothing ships to the client but the links.
 *
 * i18n mirrors the other instrument screens: ru/en inline, English for the
 * other configured locales (de/es/fr) until real copy exists — no fabricated
 * translations. The global Header supplies the chrome; this page renders none.
 */

type Lang = 'ru' | 'en';

interface Tool {
  id: string;
  path: string;
  eyebrow: {ru: string; en: string};
  title: {ru: string; en: string};
  desc: {ru: string; en: string};
}

const TOOLS: Tool[] = [
  {
    id: 'natal',
    path: 'natal',
    eyebrow: {ru: 'Swiss Ephemeris', en: 'Swiss Ephemeris'},
    title: {ru: 'Натальная карта', en: 'Natal chart'},
    desc: {
      ru: 'Положения до угловой минуты, аспекты с орбом и сходимостью, дома в четырёх системах — и кто из планет меняет дом.',
      en: 'Positions to the arcminute, aspects with orb and applying/separating, houses in four systems — and which planets change house.',
    },
  },
  {
    id: 'astrocartography',
    path: 'astrocartography',
    eyebrow: {ru: 'карта мира', en: 'world map'},
    title: {ru: 'Астрокартография', en: 'Astrocartography'},
    desc: {
      ru: 'Линии планет по карте мира: где какое влияние усиливается — по вашим данным рождения, а не по общим приметам.',
      en: 'Planetary lines across the world map: where each influence intensifies — from your birth data, not generic omens.',
    },
  },
  {
    id: 'calendar',
    path: 'calendar',
    eyebrow: {ru: 'фаза · лунный день', en: 'phase · lunar day'},
    title: {ru: 'Лунный календарь', en: 'Lunar calendar'},
    desc: {
      ru: 'Фаза и лунный день с точным JD_UT и часовым поясом — прямо из эфемерид, без выдуманных чисел.',
      en: 'Phase and lunar day with an exact JD_UT and timezone — straight from the ephemeris, no invented figures.',
    },
  },
  {
    id: 'dreams',
    path: 'dreams',
    eyebrow: {ru: 'Холл — Ван де Касл', en: 'Hall / Van de Castle'},
    title: {ru: 'Анализ снов', en: 'Dream analysis'},
    desc: {
      ru: 'Структурное кодирование: персонажи, действия, исходы — со сравнением с нормами исследования 1966 года.',
      en: 'Structural coding: characters, acts, outcomes — compared against the 1966 study’s normative data.',
    },
  },
];

const COPY = {
  ru: {
    eyebrow: 'инструментальная астрология · сны · луна',
    titleA: 'Считаем, ',
    titleEm: 'а не гадаем',
    subtitle:
      'Астрономия по Swiss Ephemeris, анализ снов по Холлу — Ван де Каслу и лунный календарь. '
      + 'Числа воспроизводимы до угловых секунд; толкование — традиция, всегда с указанием источника.',
    open: 'Открыть',
    disclaimerLead: 'Расчёт проверяем, толкование — традиция.',
    disclaimer:
      'Рефлексивный / развлекательный контент — не медицинская, психологическая, юридическая '
      + 'или финансовая консультация, без абсолютных предсказаний.',
  },
  en: {
    eyebrow: 'instrument astrology · dreams · moon',
    titleA: 'We compute, ',
    titleEm: 'we don’t divine',
    subtitle:
      'Astronomy from Swiss Ephemeris, dream analysis by Hall — Van de Castle, and a lunar calendar. '
      + 'The numbers are reproducible to arcseconds; interpretation is tradition, always with its source cited.',
    open: 'Open',
    disclaimerLead: 'The maths is verifiable; the meaning is tradition.',
    disclaimer:
      'Reflective / entertainment content — not medical, psychological, legal or financial advice, '
      + 'and no absolute predictions.',
  },
} as const;

export default function HomePage({params}: {params: {locale: string}}) {
  const lang: Lang = params.locale === 'ru' ? 'ru' : 'en';
  const locale = params.locale;
  const t = COPY[lang];

  return (
    <main style={{padding: 'clamp(16px,3vw,48px)', maxWidth: 1100, margin: '0 auto'}}>
      {/* hero */}
      <header style={{paddingBottom: 'clamp(16px,2vw,26px)', borderBottom: '1px solid var(--grat-1)'}}>
        <span className="eyebrow">{t.eyebrow}</span>
        <h1 style={{fontSize: 'clamp(32px,6vw,64px)', margin: '6px 0 0'}}>
          {t.titleA}
          <em>{t.titleEm}</em>
        </h1>
        <p style={{color: 'var(--muted)', fontSize: 15, lineHeight: 1.6, maxWidth: '60ch', marginTop: 14}}>
          {t.subtitle}
        </p>
      </header>

      {/* instrument index */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(258px, 1fr))',
          gap: 'clamp(10px,1.4vw,16px)',
          marginTop: 'clamp(18px,2.4vw,30px)',
        }}
      >
        {TOOLS.map((tool) => (
          <Link key={tool.id} href={`/${locale}/${tool.path}`} className="tool-card">
            <span className="eyebrow" style={{display: 'block'}}>{tool.eyebrow[lang]}</span>
            <h2
              className="display"
              style={{fontSize: 24, margin: '9px 0 0', color: 'var(--parchment)'}}
            >
              {tool.title[lang]}
            </h2>
            <p style={{color: 'var(--muted)', fontSize: 13, lineHeight: 1.55, margin: '9px 0 0'}}>
              {tool.desc[lang]}
            </p>
            {/* Resting colour + transition come from the .tool-open class in
                globals.css so the hover/focus recolour can actually win — an
                inline colour here would outrank it. */}
            <span className="tool-open num" style={{display: 'inline-block', marginTop: 14}}>
              {t.open} →
            </span>
          </Link>
        ))}
      </div>

      {/* house rule + mandatory disclaimer */}
      <p
        style={{
          color: 'var(--muted)',
          fontSize: 12.5,
          lineHeight: 1.6,
          marginTop: 'clamp(20px,2.6vw,32px)',
          maxWidth: '68ch',
        }}
      >
        <b style={{color: 'var(--parchment)', fontWeight: 500}}>{t.disclaimerLead}</b> {t.disclaimer}
      </p>
    </main>
  );
}
