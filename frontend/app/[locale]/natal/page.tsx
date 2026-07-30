'use client';

/**
 * Natal wheel — screen 1 of the instrument design system.
 *
 * Ported from the `public/natal.html` prototype into the Next build so the
 * geometry now comes from `@oneiroscope/chart-kit` (transpiled from source,
 * one implementation shared with the server and the golden tests) instead of
 * a committed bundle. This page never computes an ephemeris: everything below
 * is DERIVED from a `chart_core`, client-side, for free — angles, cusps,
 * aspects, houses and the lunar day. The one call that needs the server is
 * `fetchChart`, the single paid door; offline, a saved core still renders in
 * full.
 *
 * Mandatory data rules (non-negotiable, domain.md):
 *  1. positions are degree + arcminute, never a bare sign;
 *  2. aspects carry orb AND applying/separating;
 *  3. a body within 1° of a cusp is flagged borderline (±), not rounded;
 *  4. the birth block states the zone and the historical UTC offset used;
 *  5. a provenance strip proves which engine/epoch produced the numbers.
 * The house-system switcher (Ф-3) additionally names which planets change
 * house — the comparison nobody else shows.
 */

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  aspects,
  angles,
  degreeInSign,
  houseCusps,
  houseOf,
  houses,
  lunarDay,
  norm360,
  resolveSystemFor,
  sep180,
  wheelLayout,
  type ChartCore,
  type HouseSystem,
} from '@oneiroscope/chart-kit';
import {
  ChartFetchError,
  fetchChart,
  lastChart,
  saveChart,
  type ChartProvenance,
} from '@/lib/chart-store';
import { DEMO_CORE } from '@/lib/demo-chart';

// ── language-neutral glyphs ─────────────────────────────────────────────────
const SIGN_GLYPH = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
const SIGN_EN = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra',
  'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'];
const P_GLYPH: Record<string, string> = {
  Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂', Jupiter: '♃',
  Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇', TrueNode: '☊', Chiron: '⚷',
};
const MINOR = new Set(['sextile', 'quincunx']);

type Lang = 'ru' | 'en';

// ── bilingual labels (RU-first prototype, EN for /en/natal) ──────────────────
const SIGN_NAME: Record<Lang, string[]> = {
  ru: ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева', 'Весы', 'Скорпион',
    'Стрелец', 'Козерог', 'Водолей', 'Рыбы'],
  en: ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
    'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'],
};
const P_NAME: Record<Lang, Record<string, string>> = {
  ru: {
    Sun: 'Солнце', Moon: 'Луна', Mercury: 'Меркурий', Venus: 'Венера', Mars: 'Марс',
    Jupiter: 'Юпитер', Saturn: 'Сатурн', Uranus: 'Уран', Neptune: 'Нептун',
    Pluto: 'Плутон', TrueNode: 'Сев. узел', Chiron: 'Хирон',
  },
  en: {
    Sun: 'Sun', Moon: 'Moon', Mercury: 'Mercury', Venus: 'Venus', Mars: 'Mars',
    Jupiter: 'Jupiter', Saturn: 'Saturn', Uranus: 'Uranus', Neptune: 'Neptune',
    Pluto: 'Pluto', TrueNode: 'N. Node', Chiron: 'Chiron',
  },
};
const ASP_NAME: Record<Lang, Record<string, string>> = {
  ru: { conjunction: 'соединение', opposition: 'оппозиция', trine: 'трин',
    square: 'квадрат', sextile: 'секстиль', quincunx: 'квинконс' },
  en: { conjunction: 'conjunction', opposition: 'opposition', trine: 'trine',
    square: 'square', sextile: 'sextile', quincunx: 'quincunx' },
};
const SYS_NAME: Record<Lang, Record<string, string>> = {
  ru: { placidus: 'Плацидус', porphyry: 'Порфирий', whole_sign: 'по знакам', equal: 'равнодомная' },
  en: { placidus: 'Placidus', porphyry: 'Porphyry', whole_sign: 'whole sign', equal: 'equal' },
};
const PHASE_NAME: Record<Lang, Record<string, string>> = {
  ru: { new_moon: 'новолуние', waxing_crescent: 'растущий серп', first_quarter: 'первая четверть',
    waxing_gibbous: 'растущая', full_moon: 'полнолуние', waning_gibbous: 'убывающая',
    last_quarter: 'последняя четверть', waning_crescent: 'убывающий серп' },
  en: { new_moon: 'new moon', waxing_crescent: 'waxing crescent', first_quarter: 'first quarter',
    waxing_gibbous: 'waxing gibbous', full_moon: 'full moon', waning_gibbous: 'waning gibbous',
    last_quarter: 'last quarter', waning_crescent: 'waning crescent' },
};

function ui(lang: Lang) {
  const ru = {
    eyebrow: 'натальная карта', titleA: 'Где что ', titleEm: 'звучит',
    subjectSaved: 'сохранённая карта · открыта без сети',
    houseSystem: 'Система домов', angles: 'Углы', positions: 'Положения',
    aspectsHdr: 'Аспекты · орб · сходится/расходится', houses: 'Дома', natalMoon: 'Луна рождения',
    sysPlacidus: 'Плацидус', sysPorphyry: 'Порфирий', sysWhole: 'По знакам',
    moversPrefix: 'Меняют дом против Плацидуса: ', moversNone: 'Против Плацидуса дом не меняет никто.',
    noTime: 'нет времени рождения — недоступно', noWheel: 'Без времени рождения углы и дома произвольны — колесо не строится.',
    noAspects: 'в пределах орбов нет', ascNote: 'Asc слева, против часовой',
    lunarDay: 'лунный день', phase: 'фаза', moonSign: 'Луна в знаке',
    yourData: 'Ваши данные', date: 'Дата', time: 'Время', lat: 'Широта', lon: 'Долгота',
    place: 'Место', tz: 'Часовой пояс', build: 'Построить карту', building: 'Считаем…',
    disclaimerLead: 'Расчёт проверяем, толкование — традиция.',
    disclaimer: 'Геометрия карты вычислена по Swiss Ephemeris и воспроизводима до угловых секунд; '
      + 'смысл домов, аспектов и знаков — это традиция интерпретации, а не предсказание, и не '
      + 'медицинская, психологическая, юридическая или финансовая консультация.',
    offline: 'Офлайн. Сохранённая карта работает целиком; новый расчёт требует сети.',
    noNet: 'Нет сети. Новый расчёт требует сервера — сохранённая карта работает без него.',
    resetAt: 'Сбрасывается: ', account: 'Кабинет', accessLimited: 'Доступ ограничен.',
    prov: { engine: 'движок', ephem: 'эфемериды', st: 'ST', data: 'данные', demo: 'демо-карта',
      housesLbl: 'дома', tilt: 'наклон' },
    substituted: (s: string) => `(замена: ${s} здесь не определён)`,
  };
  const en = {
    eyebrow: 'natal chart', titleA: 'Where it ', titleEm: 'resonates',
    subjectSaved: 'saved chart · opened offline',
    houseSystem: 'House system', angles: 'Angles', positions: 'Positions',
    aspectsHdr: 'Aspects · orb · applying/separating', houses: 'Houses', natalMoon: 'Natal Moon',
    sysPlacidus: 'Placidus', sysPorphyry: 'Porphyry', sysWhole: 'Whole sign',
    moversPrefix: 'Change house vs Placidus: ', moversNone: 'Nothing changes house vs Placidus.',
    noTime: 'no birth time — unavailable', noWheel: 'Without a birth time the angles and houses are arbitrary — no wheel is drawn.',
    noAspects: 'none within orb', ascNote: 'Asc left, counter-clockwise',
    lunarDay: 'lunar day', phase: 'phase', moonSign: 'Moon in sign',
    yourData: 'Your data', date: 'Date', time: 'Time', lat: 'Latitude', lon: 'Longitude',
    place: 'Place', tz: 'Timezone', build: 'Build chart', building: 'Computing…',
    disclaimerLead: 'The maths is verifiable; the meaning is tradition.',
    disclaimer: 'The chart geometry is computed with Swiss Ephemeris and reproducible to arcseconds; '
      + 'the meaning of houses, aspects and signs is a tradition of interpretation, not a prediction, and not '
      + 'medical, psychological, legal or financial advice.',
    offline: 'Offline. A saved chart works in full; a new computation needs the network.',
    noNet: 'No network. A new computation needs the server — a saved chart works without it.',
    resetAt: 'Resets: ', account: 'Account', accessLimited: 'Access limited.',
    prov: { engine: 'engine', ephem: 'ephemeris', st: 'ST', data: 'data', demo: 'demo chart',
      housesLbl: 'houses', tilt: 'obliquity' },
    substituted: (s: string) => `(substituted: ${s} undefined here)`,
  };
  return lang === 'ru' ? ru : en;
}

// ── small helpers ───────────────────────────────────────────────────────────
const RAD = Math.PI / 180;
const WHEEL = 600; // viewBox units; CSS scales width:100%, so this is resolution-free
const sIdx = (lon: number): number => Math.floor(norm360(lon) / 30) % 12;
/** Colour is a token, never a hardcoded hex — read the planet metal via var(). */
const planetVar = (body: string): string => `var(--p-${body.toLowerCase()})`;
const n2 = (v: number): string => v.toFixed(2);

/** Sign glyph + degrees°arcminutes′ — never a bare sign (mandatory rule 1). */
function pos(lon: number): string {
  const d = degreeInSign(lon);
  const deg = Math.floor(d);
  let min = Math.round((d - deg) * 60);
  let dd = deg;
  if (min === 60) { min = 0; dd += 1; }
  return `${SIGN_GLYPH[sIdx(lon)]} ${dd}°${String(min).padStart(2, '0')}′`;
}

/** Ecliptic longitude → screen point, Asc on the left, counter-clockwise. */
const pt = (cx: number, cy: number, r: number, lon: number, asc: number): [number, number] => {
  const a = (lon - asc) * RAD;
  return [cx - r * Math.cos(a), cy + r * Math.sin(a)];
};

/**
 * The system actually drawable at the birth latitude: past the polar circle
 * Placidus/Koch are undefined, so a chart there gets the honest Porphyry
 * substitution the server and kit both use, never a crash.
 */
function effSystem(core: ChartCore, system: HouseSystem): HouseSystem {
  const { lat, lon } = core.birth;
  if (system === 'placidus' || system === 'koch') {
    try { houseCusps(core, lat, lon, system); return system; }
    catch { return resolveSystemFor(core, lat, lon).system; }
  }
  return system;
}

/** Bodies within 1° of any cusp — flagged, not rounded (mandatory rule 3). */
function borderlineSet(core: ChartCore, cusps: number[]): Set<string> {
  const near = new Set<string>();
  for (const [name, body] of Object.entries(core.bodies)) {
    for (const cusp of cusps) {
      if (Math.abs(sep180(body.ecl_lon, cusp)) < 1) { near.add(name); break; }
    }
  }
  return near;
}

interface Notice { text: string; accountUrl?: string; resetAt?: string | null; }

export default function NatalPage() {
  const params = useParams();
  const lang: Lang = params?.locale === 'ru' ? 'ru' : 'en';
  const t = ui(lang);
  const hAbbr = lang === 'ru' ? 'д' : 'h'; // house prefix: «дом» / house

  const [core, setCore] = useState<ChartCore>(DEMO_CORE);
  const [prov, setProv] = useState<ChartProvenance | null>(null);
  const [system, setSystem] = useState<HouseSystem>('placidus');
  const [notice, setNotice] = useState<Notice | null>(null);
  const [savedNote, setSavedNote] = useState(false);
  const [busy, setBusy] = useState(false);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);

  // form fields
  const [bdate, setBdate] = useState('1977-07-01');
  const [btime, setBtime] = useState('22:30');
  const [blat, setBlat] = useState('47.8388');
  const [blon, setBlon] = useState('35.1396');
  const [bplace, setBplace] = useState('Запорожье');
  const [btz, setBtz] = useState('Europe/Kyiv');

  // Restore the most recent saved chart (opens with no network).
  useEffect(() => {
    let alive = true;
    lastChart().then((saved) => {
      if (!alive || !saved) return;
      setCore(saved);
      setSystem((saved.house_system as HouseSystem) || 'placidus');
      setSavedNote(true);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    const off = () => setNotice({ text: t.offline });
    const on = () => setNotice(null);
    window.addEventListener('offline', off);
    window.addEventListener('online', on);
    return () => {
      window.removeEventListener('offline', off);
      window.removeEventListener('online', on);
    };
  }, [t.offline]);

  // Everything shown is derived from (core, system) — no ephemeris, no network.
  const view = useMemo(() => {
    const b = core.birth;
    const timed = b.time_known;
    const useSystem = timed ? effSystem(core, system) : system;

    let cusps: number[] | null = null;
    let border = new Set<string>();
    if (timed) {
      try {
        cusps = houseCusps(core, b.lat, b.lon, useSystem);
        border = borderlineSet(core, cusps);
      } catch { cusps = null; }
    }

    // House-system movers (Ф-3): who changes house vs Placidus. Undefined at
    // the poles (Placidus itself substituted), so guard rather than throw.
    let movers: string[] | null = null;
    if (timed && system !== 'placidus') {
      try {
        const base = houseCusps(core, b.lat, b.lon, 'placidus');
        const cur = houseCusps(core, b.lat, b.lon, useSystem);
        movers = [];
        for (const [name, body] of Object.entries(core.bodies)) {
          const h0 = houseOf(body.ecl_lon, base);
          const h1 = houseOf(body.ecl_lon, cur);
          if (h0 !== h1) movers.push(`${P_GLYPH[name]} ${hAbbr}${h0}→${h1}`);
        }
      } catch { movers = null; }
    }

    const wheel = timed
      ? wheelLayout(core, b.lat, b.lon, { size: WHEEL, system: useSystem, minGlyphGap: 7 })
      : null;

    const angs = timed ? angles(core, b.lat, b.lon) : null;
    const asps = aspects(core);
    const houseList = timed ? houses(core, b.lat, b.lon, useSystem) : null;
    const lunar = lunarDay(core);

    return { b, timed, useSystem, cusps, border, movers, wheel, angs, asps, houseList, lunar };
  }, [core, system, hAbbr]);

  async function onSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!navigator.onLine) { setNotice({ text: t.noNet }); return; }
    setBusy(true);
    try {
      const data = await fetchChart({
        birth_date: bdate,
        birth_time: btime ? `${btime}:00` : null,
        birth_place: bplace || (lang === 'ru' ? 'рождение' : 'birth'),
        latitude: parseFloat(blat),
        longitude: parseFloat(blon),
        timezone_name: btz,
        locale: lang,
      });
      setCore(data.chart_core);
      setProv(data.provenance || null);
      setSystem((data.chart_core.house_system as HouseSystem) || 'placidus');
      setSavedNote(false);
      setNotice(null);
      if (data.disclaimer) setDisclaimer(data.disclaimer);
      await saveChart(data.chart_core);
    } catch (err) {
      if (err instanceof ChartFetchError && (err.status === 401 || err.status === 402)) {
        const d = err.detail;
        setNotice({
          text: d?.message || t.accessLimited,
          accountUrl: d?.account_url,
          resetAt: d?.reset_at ?? null,
        });
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        setNotice({ text: msg });
      }
    } finally {
      setBusy(false);
    }
  }

  const v = view;
  const R = v.wheel?.radii;
  const c = v.wheel?.center;
  const asc = v.wheel?.asc ?? 0;
  const wheelSubstituted = v.wheel ? (v.wheel.system !== system || v.wheel.substituted) : false;

  return (
    <main style={{ padding: 'clamp(14px,2.2vw,30px)' }}>
      <header style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: '12px 28px',
        paddingBottom: 14, marginBottom: 'clamp(12px,1.6vw,20px)',
        borderBottom: '1px solid var(--grat-1)',
      }}>
        <div>
          <span className="eyebrow">{t.eyebrow}</span>
          <h1 style={{ fontSize: 'clamp(28px,5vw,52px)', margin: 0 }}>
            {t.titleA}<em>{t.titleEm}</em>
          </h1>
        </div>
        <div className="num" style={{
          marginLeft: 'auto', textAlign: 'right', fontSize: 11.5, lineHeight: 1.7, color: 'var(--muted)',
        }}>
          <b style={{ color: 'var(--parchment)', fontWeight: 500 }}>{v.b.place_label || '—'}</b><br />
          {v.b.local_clock.replace('T', ' ')}<br />
          {v.b.lat}°, {v.b.lon}° · {v.b.tz_used} {v.b.utc_offset_used}
          {savedNote && (
            <><br /><span style={{ color: 'var(--brass)' }}>{t.subjectSaved}</span></>
          )}
        </div>
      </header>

      <div className="stage">
        {/* ── wheel ── */}
        <div style={{ position: 'relative', border: '1px solid var(--grat-2)', background: 'var(--shelf)' }}>
          {v.wheel && R && c ? (
            <svg viewBox={`0 0 ${WHEEL} ${WHEEL}`} role="img" aria-label="Натальное колесо"
              style={{ display: 'block', width: '100%', height: 'auto' }}>
              {/* rings */}
              {([[R.outer, 0.5], [R.zodiac, 0.32], [R.glyphs, 0.16], [R.aspects, 0.22]] as const).map(([r, op], i) => (
                <circle key={`ring${i}`} cx={n2(c.x)} cy={n2(c.y)} r={n2(r)} fill="none"
                  style={{ stroke: 'var(--grat-2)' }} strokeOpacity={op} />
              ))}
              {/* degree scale: tick every 5°, long every 30° (sign boundary) */}
              {Array.from({ length: 72 }, (_, k) => {
                const deg = k * 5;
                const major = deg % 30 === 0;
                const [x1, y1] = pt(c.x, c.y, R.outer, deg, asc);
                const [x2, y2] = pt(c.x, c.y, R.outer - (major ? 12 : 6), deg, asc);
                return (
                  <line key={`tick${k}`} x1={n2(x1)} y1={n2(y1)} x2={n2(x2)} y2={n2(y2)}
                    style={{ stroke: 'var(--brass)' }} strokeOpacity={major ? 0.7 : 0.28}
                    strokeWidth={major ? 1 : 0.7} />
                );
              })}
              {/* sign glyphs on the scale */}
              {Array.from({ length: 12 }, (_, s) => {
                const [x, y] = pt(c.x, c.y, R.outer - 24, s * 30 + 15, asc);
                return (
                  <text key={`sg${s}`} x={n2(x)} y={n2(y)} textAnchor="middle" dominantBaseline="central"
                    fontSize={n2(WHEEL * 0.026)} style={{ fill: 'var(--brass)' }} fillOpacity={0.8}
                    fontFamily="var(--font-data)">{SIGN_GLYPH[s]}</text>
                );
              })}
              {/* aspect chords — coloured by first body's metal, dashed for minor */}
              {v.wheel.chords.map((ch, i) => (
                <line key={`chord${i}`} x1={n2(ch.from.x)} y1={n2(ch.from.y)} x2={n2(ch.to.x)} y2={n2(ch.to.y)}
                  style={{ stroke: planetVar(ch.a) }} strokeOpacity={ch.applying ? 0.85 : 0.45}
                  strokeWidth={ch.type === 'conjunction' ? 1.3 : 1}
                  strokeDasharray={MINOR.has(ch.type) ? '2 3' : undefined} />
              ))}
              {/* cusp spokes — angles heavier + brass, others thin */}
              {v.wheel.spokes.map((sp, i) => (
                <line key={`spoke${i}`} x1={n2(sp.from.x)} y1={n2(sp.from.y)} x2={n2(sp.to.x)} y2={n2(sp.to.y)}
                  style={{ stroke: sp.isAngle ? 'var(--brass)' : 'var(--grat-2)' }}
                  strokeOpacity={sp.isAngle ? 0.75 : 0.5} strokeWidth={sp.isAngle ? 1.6 : 0.8} />
              ))}
              {/* planets — metal colour, tick back to true position, retrograde mark */}
              {v.wheel.glyphs.map((g, i) => (
                <g key={`glyph${i}`}>
                  <line x1={n2(g.tick[0].x)} y1={n2(g.tick[0].y)} x2={n2(g.tick[1].x)} y2={n2(g.tick[1].y)}
                    style={{ stroke: planetVar(g.body) }} strokeOpacity={0.55} />
                  <text x={n2(g.at.x)} y={n2(g.at.y)} textAnchor="middle" dominantBaseline="central"
                    fontSize={n2(WHEEL * 0.033)} style={{ fill: planetVar(g.body) }}>
                    {P_GLYPH[g.body] || g.body}
                    {g.retrograde && (
                      <tspan fontSize="58%" dy="-.55em" style={{ fill: 'var(--brass)' }}>℞</tspan>
                    )}
                  </text>
                </g>
              ))}
            </svg>
          ) : (
            <div style={{ padding: '40px 20px', fontFamily: 'var(--font-data)', fontSize: 12, color: 'var(--dim)' }}>
              {t.noWheel}
            </div>
          )}
          {v.wheel && (
            <div style={{
              position: 'absolute', left: 12, bottom: 10, fontFamily: 'var(--font-data)',
              fontSize: 10, color: 'var(--dim)', letterSpacing: '.04em', maxWidth: '70%',
            }}>
              {SYS_NAME[lang][v.wheel.system] || v.wheel.system}
              {wheelSubstituted ? ` ${t.substituted(SYS_NAME[lang][system] || system)}` : ''} · {t.ascNote}
            </div>
          )}
        </div>

        {/* ── panel ── */}
        <div>
          <div className="panel">
            {/* house-system switcher (Ф-3) */}
            <div className="panel-block">
              <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>{t.houseSystem}</span>
              <div style={{ display: 'flex', border: '1px solid var(--grat-2)', marginTop: 2 }}>
                {([['placidus', t.sysPlacidus], ['porphyry', t.sysPorphyry], ['whole_sign', t.sysWhole]] as const).map(
                  ([sys, label], i) => (
                    <button key={sys} type="button" onClick={() => setSystem(sys)}
                      style={{
                        flex: 1, background: system === sys ? 'var(--panel)' : 'transparent',
                        color: system === sys ? 'var(--brass)' : 'var(--muted)', border: 0,
                        borderRight: i < 2 ? '1px solid var(--grat-1)' : 0, fontFamily: 'var(--font-data)',
                        fontSize: 11, letterSpacing: '.03em', padding: '7px 4px', cursor: 'pointer',
                      }}>{label}</button>
                  ),
                )}
              </div>
              {v.movers !== null && (
                <div style={{ fontFamily: 'var(--font-data)', fontSize: 11, color: 'var(--dim)', marginTop: 8, lineHeight: 1.5 }}>
                  {v.movers.length
                    ? <>{t.moversPrefix}<span style={{ color: 'var(--brass)' }}>{v.movers.join(' · ')}</span></>
                    : t.moversNone}
                </div>
              )}
            </div>

            {/* angles */}
            <PanelTable title={t.angles}>
              {v.angs ? (
                ([['ASC', v.angs.asc], ['MC', v.angs.mc], ['DSC', v.angs.desc], ['IC', v.angs.ic]] as const).map(
                  ([nm, val]) => (
                    <tr key={nm}><td>{nm}</td><td style={rCell}>{pos(val)}</td></tr>
                  ),
                )
              ) : (
                <tr><td colSpan={2} style={{ color: 'var(--muted)' }}>{t.noTime}</td></tr>
              )}
            </PanelTable>

            {/* positions: degree+arcminute, retrograde, house, borderline */}
            <PanelTable title={t.positions}>
              {Object.entries(core.bodies).map(([name, body]) => (
                <tr key={name}>
                  <td>
                    <span style={{ display: 'inline-block', width: '1.1em', textAlign: 'center', marginRight: 5, color: planetVar(name) }}>
                      {P_GLYPH[name]}
                    </span>
                    {P_NAME[lang][name]}
                    {body.retrograde && <span style={{ color: 'var(--brass)', fontSize: '.82em' }}> ℞</span>}
                  </td>
                  <td style={{ ...rCell, color: v.border.has(name) ? 'var(--brass)' : 'var(--muted)' }}>
                    {pos(body.ecl_lon)}{v.timed && v.cusps ? ` · ${hAbbr}${houseOf(body.ecl_lon, v.cusps)}` : ''}{v.border.has(name) ? ' ±' : ''}
                  </td>
                </tr>
              ))}
            </PanelTable>

            {/* aspects: orb + applying/separating (mandatory rule 2) */}
            <PanelTable title={t.aspectsHdr}>
              {v.asps.length ? (
                v.asps.map((x, i) => (
                  <tr key={i}>
                    <td>
                      <span style={{ color: planetVar(x.a) }}>{P_GLYPH[x.a]}</span> {ASP_NAME[lang][x.type]}{' '}
                      <span style={{ color: planetVar(x.b) }}>{P_GLYPH[x.b]}</span>
                    </td>
                    <td style={rCell}>
                      <span style={{ color: x.applying ? 'var(--parchment)' : 'var(--dim)' }}>
                        {x.orb.toFixed(2)}° {x.applying ? (lang === 'ru' ? 'сходится' : 'applying') : (lang === 'ru' ? 'расходится' : 'separating')}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={2} style={{ color: 'var(--muted)' }}>{t.noAspects}</td></tr>
              )}
            </PanelTable>

            {/* houses */}
            <PanelTable title={t.houses}>
              {v.houseList ? (
                v.houseList.map((h) => (
                  <tr key={h.number}>
                    <td>{h.number}</td>
                    <td style={rCell}>
                      {pos(h.cusp)}
                      {h.bodies.length ? <span style={{ color: 'var(--brass)' }}> {h.bodies.map((x) => P_GLYPH[x]).join('')}</span> : ''}
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={2} style={{ color: 'var(--muted)' }}>{t.noTime}</td></tr>
              )}
            </PanelTable>

            {/* lunar day of birth (exact server formula, no illumination) */}
            <PanelTable title={t.natalMoon}>
              <tr><td>{t.lunarDay}</td><td style={rCell}>{v.lunar.lunarDay}</td></tr>
              <tr><td>{t.phase}</td><td style={rCell}>{PHASE_NAME[lang][v.lunar.phase] || v.lunar.phase}</td></tr>
              <tr>
                <td>{t.moonSign}</td>
                <td style={rCell}>
                  {SIGN_GLYPH[SIGN_EN.indexOf(v.lunar.moonSign)] || ''} {SIGN_NAME[lang][SIGN_EN.indexOf(v.lunar.moonSign)] || v.lunar.moonSign}
                </td>
              </tr>
            </PanelTable>
          </div>

          {/* birth-data entry — a real chart is the one paid, gated call */}
          <form onSubmit={onSubmit} style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px', marginTop: 14 }}>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>{t.yourData}</span>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Field label={t.date}><input type="date" value={bdate} onChange={(e) => setBdate(e.target.value)} style={inputStyle} /></Field>
              <Field label={t.time}><input type="time" value={btime} onChange={(e) => setBtime(e.target.value)} style={inputStyle} /></Field>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 8 }}>
              <Field label={t.lat}><input type="number" step="0.0001" value={blat} onChange={(e) => setBlat(e.target.value)} style={inputStyle} /></Field>
              <Field label={t.lon}><input type="number" step="0.0001" value={blon} onChange={(e) => setBlon(e.target.value)} style={inputStyle} /></Field>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 8 }}>
              <Field label={t.place}><input type="text" value={bplace} onChange={(e) => setBplace(e.target.value)} style={inputStyle} /></Field>
              <Field label={t.tz}>
                <select value={btz} onChange={(e) => setBtz(e.target.value)} style={inputStyle}>
                  {['Europe/Kyiv', 'Europe/Moscow', 'Europe/Prague', 'Europe/Madrid', 'Asia/Tokyo', 'UTC'].map((z) => (
                    <option key={z} value={z}>{z}</option>
                  ))}
                </select>
              </Field>
            </div>
            <button type="submit" disabled={busy} style={{
              marginTop: 11, width: '100%', background: 'var(--brass)', color: 'var(--abyss)', border: 0,
              fontFamily: 'var(--font-ui)', fontWeight: 600, padding: 9, cursor: busy ? 'not-allowed' : 'pointer',
              letterSpacing: '.02em', opacity: busy ? 0.45 : 1,
            }}>{busy ? t.building : t.build}</button>
          </form>

          {notice && (
            <div style={{
              border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)', color: 'var(--notice-ink)',
              padding: '9px 12px', fontSize: 12.5, lineHeight: 1.5, marginTop: 12,
            }}>
              {notice.text}
              {notice.resetAt ? ` ${t.resetAt}${notice.resetAt}.` : ''}
              {notice.accountUrl && <> <a href={notice.accountUrl} style={{ color: 'var(--brass)' }}>{t.account}</a></>}
            </div>
          )}
        </div>
      </div>

      <p style={{ color: 'var(--muted)', fontSize: 12, lineHeight: 1.55, marginTop: 14, maxWidth: '64ch' }}>
        <b style={{ color: 'var(--parchment)', fontWeight: 500 }}>{t.disclaimerLead}</b> {disclaimer || t.disclaimer}
      </p>

      {/* provenance strip — proof of work, mandatory on every computed screen */}
      <div className="provenance" style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 18px' }}>
        {prov ? (
          <>
            <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.engine}</b> {prov.ephemeris_engine || 'SWIEPH'}</span>
            {prov.ephemeris_version && <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.ephem}</b> {prov.ephemeris_version}</span>}
            {prov.sidereal_time && <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.st}</b> {prov.sidereal_time}</span>}
          </>
        ) : (
          <>
            <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.engine}</b> Swiss Ephemeris (SWIEPH)</span>
            <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.data}</b> {t.prov.demo}</span>
          </>
        )}
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.housesLbl}</b> {SYS_NAME[lang][system] || system}</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>GMST</b> {core.gmst.toFixed(4)}°</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.prov.tilt}</b> {core.obliquity.toFixed(5)}°</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>JD_UT</b> {core.jd_ut}</span>
      </div>
    </main>
  );
}

// ── presentational helpers ──────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: '100%', background: 'var(--abyss)', color: 'var(--parchment)',
  border: '1px solid var(--grat-2)', fontFamily: 'var(--font-data)', fontSize: 12, padding: '6px 8px',
};

/** Right-aligned data cell. Borderline colour/marker is applied inline at the
 *  call site (rule 3) rather than via a class, to avoid a specificity clash. */
const rCell: React.CSSProperties = { textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--muted)' };

function PanelTable({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel-block">
      <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>{title}</span>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: 12 }}
        className="num">
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ flex: 1, minWidth: 120 }}>
      <label style={{
        display: 'block', color: 'var(--dim)', fontFamily: 'var(--font-data)', fontSize: 10,
        letterSpacing: '.04em', textTransform: 'uppercase', margin: '0 0 3px',
      }}>{label}</label>
      {children}
    </div>
  );
}
