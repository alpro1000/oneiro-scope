'use client';

/**
 * Astrocartography — the strongest module Co-Star does not have.
 *
 * Ported from the instrument reference (`astrocartography.html` in the repo
 * root) into the Next build. The map is a hand-drawn equirectangular canvas —
 * nautical chart, not a tile service — so it is self-contained and works with
 * the radio off: coastlines are static geography, and every line, angle and
 * contact is DERIVED from one `chart_core` by `@oneiroscope/chart-kit`
 * (`acgLines`, `angles`, `contacts`), never re-implemented here. Duplicating
 * those formulas is exactly how a client starts drawing a chart the server
 * would never have produced.
 *
 * Move the cursor (or touch): the panel reads the four angles at that point
 * and which planets sit on them within 8°. The one networked act is fetching
 * a real chart — the single gated call; offline, a saved core still maps.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  acgLines,
  angles as kitAngles,
  contacts as kitContacts,
  norm360,
  type ChartCore,
} from '@oneiroscope/chart-kit';
import {
  ChartFetchError,
  fetchChart,
  lastChart,
  saveChart,
  type ChartProvenance,
} from '@/lib/chart-store';
import { DEMO_CORE } from '@/lib/demo-chart';
import { WORLD_COAST } from '@/lib/world-coast';

type Lang = 'ru' | 'en';

// ── the ten classical planets get lines (matches the reference legend) ───────
const PLANETS = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
  'Uranus', 'Neptune', 'Pluto'];
const PG: Record<string, string> = {
  Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂',
  Jupiter: '♃', Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇',
};
const P_NAME: Record<Lang, Record<string, string>> = {
  ru: { Sun: 'Солнце', Moon: 'Луна', Mercury: 'Меркурий', Venus: 'Венера', Mars: 'Марс',
    Jupiter: 'Юпитер', Saturn: 'Сатурн', Uranus: 'Уран', Neptune: 'Нептун', Pluto: 'Плутон' },
  en: { Sun: 'Sun', Moon: 'Moon', Mercury: 'Mercury', Venus: 'Venus', Mars: 'Mars',
    Jupiter: 'Jupiter', Saturn: 'Saturn', Uranus: 'Uranus', Neptune: 'Neptune', Pluto: 'Pluto' },
};
const SG = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
const CITIES: [string, number, number][] = [
  ['Запорожье', 47.84, 35.14], ['Прага', 50.08, 14.44], ['Пльзень', 49.74, 13.37],
  ['Барселона', 41.39, 2.17], ['Валенсия', 39.47, -0.38], ['Малага', 36.72, -4.42],
  ['Братислава', 48.15, 17.11],
];

const LAT_T = 78, LAT_B = -58, ORB = 8;

function ui(lang: Lang) {
  const ru = {
    eyebrow: 'Astro · Carto · Graphy · Lewis 1976', titleA: 'Где ', titleEm: 'что', titleB: ' звучит',
    hint: 'ведите курсор · на телефоне — касайтесь',
    point: 'Точка', anglesHere: 'Углы в этой точке', onAngles: 'Планеты на углах · орб 8°',
    cities: 'Быстрый переход', yourData: 'Ваши данные',
    hoverPrompt: 'Наведите на карту', noneInOrb: 'Ни одной планеты в орбе 8°',
    date: 'Дата', time: 'Время', tz: 'Часовой пояс', lat: 'Широта', lon: 'Долгота',
    place: 'Место', build: 'Построить карту', building: 'Считаем…',
    engine: 'движок', lines: 'линий', tilt: 'наклон', data: 'данные', demo: 'демо-карта',
    houses: 'дома', noTime: 'нет времени рождения — астрокарта строится на углах, а они без времени произвольны',
    saved: 'сохранённая карта · открыта без сети', accessLimited: 'Доступ ограничен.',
    account: 'Кабинет', resetAt: 'Сбрасывается: ', noNet: 'Нет сети. Новый расчёт требует сервера.',
    disclaimerLead: 'Линии и углы — геометрия, она проверяема.',
    disclaimer: 'Символическое значение планеты на угле — традиция толкования, а не '
      + 'прогноз. Это рефлексивно-развлекательный материал, не медицинский, '
      + 'психологический, юридический или финансовый совет.',
  };
  const en = {
    eyebrow: 'Astro · Carto · Graphy · Lewis 1976', titleA: 'Where it ', titleEm: 'all', titleB: ' resonates',
    hint: 'move the cursor · on a phone, touch',
    point: 'Point', anglesHere: 'Angles at this point', onAngles: 'Planets on angles · orb 8°',
    cities: 'Quick jump', yourData: 'Your data',
    hoverPrompt: 'Point at the map', noneInOrb: 'No planet within 8° orb',
    date: 'Date', time: 'Time', tz: 'Timezone', lat: 'Latitude', lon: 'Longitude',
    place: 'Place', build: 'Build chart', building: 'Computing…',
    engine: 'engine', lines: 'lines', tilt: 'obliquity', data: 'data', demo: 'demo chart',
    houses: 'houses', noTime: 'no birth time — astrocartography is built on the angles, and without a time they are arbitrary',
    saved: 'saved chart · opened offline', accessLimited: 'Access limited.',
    account: 'Account', resetAt: 'Resets: ', noNet: 'No network. A new computation needs the server.',
    disclaimerLead: 'Lines and angles are geometry — verifiable.',
    disclaimer: 'The symbolic meaning of a planet on an angle is a tradition of '
      + 'interpretation, not a prediction. This is reflective/entertainment material, '
      + 'not medical, psychological, legal or financial advice.',
  };
  return lang === 'ru' ? ru : en;
}

// ── formatting ───────────────────────────────────────────────────────────────
const norm = (a: number) => norm360(a);
function fmtSign(l: number): string {
  l = norm(l);
  const s = Math.floor(l / 30) % 12;
  const d = l - Math.floor(l / 30) * 30;
  return `${SG[s]} ${Math.floor(d)}°${String(Math.round((d % 1) * 60)).padStart(2, '0')}′`;
}
const fmtLat = (v: number) => `${Math.abs(v).toFixed(2)}°${v >= 0 ? 'N' : 'S'}`;
const fmtLon = (v: number) => `${Math.abs(v).toFixed(2)}°${v >= 0 ? 'E' : 'W'}`;

interface Colors {
  abyss: string; gratMinor: string; gratMajor: string; land: string; landEdge: string;
  brass: string; parchment: string; dim: string; planet: Record<string, string>;
}
function readColors(): Colors {
  const cs = getComputedStyle(document.documentElement);
  // Colours come from tokens.css only. Canvas needs concrete strings, so the
  // custom properties are resolved here rather than referenced as var(); no
  // hex is hardcoded — a missing token degrades to the muted token or nothing.
  const v = (n: string) => cs.getPropertyValue(n).trim();
  const dim = v('--dim') || 'transparent';
  const planet: Record<string, string> = {};
  for (const p of PLANETS) planet[p] = v(`--p-${p.toLowerCase()}`) || dim;
  return {
    abyss: v('--abyss'), gratMinor: v('--grat-1'), gratMajor: v('--land-edge'),
    land: v('--land'), landEdge: v('--land-edge'), brass: v('--brass'),
    parchment: v('--parchment'), dim, planet,
  };
}

interface Cursor { lat: number; lon: number; name: string; }
interface Notice { text: string; accountUrl?: string; resetAt?: string | null; }

export default function AstrocartographyPage() {
  const params = useParams();
  const lang: Lang = params?.locale === 'ru' ? 'ru' : 'en';
  const t = ui(lang);

  const [core, setCore] = useState<ChartCore>(DEMO_CORE);
  const [cursor, setCursor] = useState<Cursor | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [prov, setProv] = useState<ChartProvenance | null>(null);
  const [colors, setColors] = useState<Colors | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0, dpr: 1 });
  const [notice, setNotice] = useState<Notice | null>(null);
  const [savedNote, setSavedNote] = useState(false);
  const [busy, setBusy] = useState(false);

  const [bdate, setBdate] = useState('1977-07-01');
  const [btime, setBtime] = useState('22:30');
  const [blat, setBlat] = useState('47.8388');
  const [blon, setBlon] = useState('35.1396');
  const [bplace, setBplace] = useState('Запорожье');
  const [btz, setBtz] = useState('Europe/Kyiv');

  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const baseRef = useRef<HTMLCanvasElement | null>(null);

  // No birth time → the whole screen is meaningless: astrocartography is
  // angle-derived, and with time unknown the angles were computed for an
  // assumed noon. The contract forbids drawing them (BirthInfo.time_known);
  // the natal route guards the same way. So: no lines, no cursor readout.
  const timed = core.birth.time_known;

  const lines = useMemo(
    () => (timed ? acgLines(core, { latRange: [LAT_B, LAT_T], bodies: PLANETS }) : []),
    [core, timed],
  );

  // Panel readout: the four angles at the cursor and which planets sit on them.
  const panel = useMemo(() => {
    if (!cursor || !timed) return null;
    const a = kitAngles(core, cursor.lat, cursor.lon);
    const cs = kitContacts(core, cursor.lat, cursor.lon, ORB)
      .filter((c) => !hidden.has(c.body))
      .sort((x, y) => x.orb - y.orb);
    return { a, contacts: cs };
  }, [core, cursor, hidden, timed]);

  const px = useCallback((lon: number, W: number) => ((lon + 180) / 360) * W, []);
  const py = useCallback((lat: number, H: number) => ((LAT_T - lat) / (LAT_T - LAT_B)) * H, []);

  // The whole scene, drawn from a cached base (graticule + land + birth mark)
  // plus the live lines and crosshair. Base is redrawn only when the chart,
  // colours or size change; the cursor only repaints the top layer.
  const drawBase = useCallback(() => {
    if (!colors || size.w === 0) return;
    if (!baseRef.current) baseRef.current = document.createElement('canvas');
    const base = baseRef.current;
    const { w: W, h: H, dpr } = size;
    base.width = W * dpr; base.height = H * dpr;
    const bx = base.getContext('2d');
    if (!bx) return;
    bx.setTransform(dpr, 0, 0, dpr, 0, 0);
    bx.fillStyle = colors.abyss; bx.fillRect(0, 0, W, H);
    bx.lineWidth = 1;
    for (let lon = -180; lon <= 180; lon += 30) {
      bx.strokeStyle = lon === 0 ? colors.gratMajor : colors.gratMinor;
      bx.beginPath(); bx.moveTo(px(lon, W), 0); bx.lineTo(px(lon, W), H); bx.stroke();
    }
    for (let lat = -40; lat <= 70; lat += 20) {
      bx.strokeStyle = lat === 0 ? colors.gratMajor : colors.gratMinor;
      bx.beginPath(); bx.moveTo(0, py(lat, H)); bx.lineTo(W, py(lat, H)); bx.stroke();
    }
    bx.fillStyle = colors.land; bx.strokeStyle = colors.landEdge; bx.lineWidth = 0.7;
    for (const poly of WORLD_COAST) {
      bx.beginPath();
      for (let i = 0; i < poly.length; i++) {
        const x = px(poly[i][0], W), y = py(poly[i][1], H);
        if (i) bx.lineTo(x, y); else bx.moveTo(x, y);
      }
      bx.closePath(); bx.fill(); bx.stroke();
    }
    const bxp = px(core.birth.lon, W), byp = py(core.birth.lat, H);
    bx.strokeStyle = colors.brass; bx.lineWidth = 1.1;
    bx.beginPath(); bx.arc(bxp, byp, 4.5, 0, 7); bx.stroke();
    bx.beginPath(); bx.arc(bxp, byp, 1.3, 0, 7); bx.fillStyle = colors.brass; bx.fill();
  }, [colors, size, core, px, py]);

  const paint = useCallback(() => {
    const cv = canvasRef.current, base = baseRef.current;
    if (!cv || !base || !colors || size.w === 0) return;
    const { w: W, h: H, dpr } = size;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.drawImage(base, 0, 0, W, H);

    const hot = new Set<string>();
    if (cursor && timed) {
      for (const c of kitContacts(core, cursor.lat, cursor.lon, ORB)) {
        hot.add(`${c.body}|${c.angle.toUpperCase()}`);
      }
    }
    for (const ln of lines) {
      if (hidden.has(ln.body)) continue;
      const isHot = hot.has(`${ln.body}|${ln.kind}`);
      const solid = ln.kind === 'MC' || ln.kind === 'ASC';
      ctx.strokeStyle = colors.planet[ln.body] || colors.parchment;
      ctx.globalAlpha = isHot ? 1 : (solid ? 0.62 : 0.4);
      ctx.lineWidth = isHot ? 2.4 : (solid ? 1.25 : 1);
      ctx.setLineDash(solid ? [] : [4, 4]);
      ctx.beginPath();
      let prev: number | null = null;
      for (const [lo, la] of ln.points) {
        if (la > LAT_T || la < LAT_B) { prev = null; continue; }
        const x = px(lo, W), y = py(la, H);
        if (prev === null || Math.abs(lo - prev) > 180) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        prev = lo;
      }
      ctx.stroke();
    }
    ctx.setLineDash([]); ctx.globalAlpha = 1;

    if (cursor) {
      const x = px(cursor.lon, W), y = py(cursor.lat, H);
      // Dotted crosshair — the design reserves dashes for IC/Desc lines and
      // dots for the cursor, so the two never read as the same mark.
      ctx.strokeStyle = colors.parchment; ctx.globalAlpha = 0.55; ctx.lineWidth = 1; ctx.setLineDash([1, 3]);
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      ctx.setLineDash([]); ctx.globalAlpha = 1;
      ctx.strokeStyle = colors.parchment; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.arc(x, y, 6, 0, 7); ctx.stroke();
    }
  }, [core, lines, hidden, cursor, colors, size, px, py, timed]);

  // colours once the stylesheet is live
  useEffect(() => { setColors(readColors()); }, []);

  // size follows the map container
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const measure = () => {
      const W = Math.max(320, wrap.clientWidth);
      const H = Math.round((W * (LAT_T - LAT_B)) / 360);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      setSize({ w: W, h: H, dpr });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, []);

  // size the visible canvas + rebuild base + paint on chart/size/colour change
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || !colors || size.w === 0) return;
    cv.width = size.w * size.dpr;
    cv.height = size.h * size.dpr;
    cv.style.height = `${size.h}px`;
    drawBase();
    paint();
  }, [size, colors, drawBase, paint]);

  // cursor / legend only repaint the top layer
  useEffect(() => { paint(); }, [cursor, hidden, paint]);

  // restore a saved chart (opens with no network)
  useEffect(() => {
    let alive = true;
    lastChart().then((saved) => {
      if (!alive || !saved) return;
      setCore(saved);
      setSavedNote(true);
    });
    return () => { alive = false; };
  }, []);

  // pointer → cursor, throttled to one update per frame
  const rafRef = useRef<number | null>(null);
  const pendRef = useRef<{ lat: number; lon: number } | null>(null);
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const move = (clientX: number, clientY: number) => {
      const r = cv.getBoundingClientRect();
      const fx = (clientX - r.left) / r.width, fy = (clientY - r.top) / r.height;
      const lat = Math.max(LAT_B, Math.min(LAT_T, LAT_T - fy * (LAT_T - LAT_B)));
      const lon = ((-180 + fx * 360 + 540) % 360) - 180;
      pendRef.current = { lat, lon };
      if (rafRef.current == null) {
        rafRef.current = requestAnimationFrame(() => {
          rafRef.current = null;
          if (pendRef.current) setCursor({ ...pendRef.current, name: '' });
        });
      }
    };
    const onMouse = (e: MouseEvent) => move(e.clientX, e.clientY);
    const onTouch = (e: TouchEvent) => {
      if (!e.touches.length) return;
      e.preventDefault();
      move(e.touches[0].clientX, e.touches[0].clientY);
    };
    cv.addEventListener('mousemove', onMouse);
    cv.addEventListener('touchstart', onTouch, { passive: false });
    cv.addEventListener('touchmove', onTouch, { passive: false });
    return () => {
      cv.removeEventListener('mousemove', onMouse);
      cv.removeEventListener('touchstart', onTouch);
      cv.removeEventListener('touchmove', onTouch);
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const toggle = (p: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p); else next.add(p);
      return next;
    });

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
      setSavedNote(false);
      setCursor(null);
      setNotice(null);
      await saveChart(data.chart_core);
    } catch (err) {
      if (err instanceof ChartFetchError && (err.status === 401 || err.status === 402)) {
        const d = err.detail;
        setNotice({ text: d?.message || t.accessLimited, accountUrl: d?.account_url, resetAt: d?.reset_at ?? null });
      } else {
        setNotice({ text: err instanceof Error ? err.message : String(err) });
      }
    } finally {
      setBusy(false);
    }
  }

  const b = core.birth;
  const planetVar = (body: string) => `var(--p-${body.toLowerCase()})`;

  return (
    <main style={{ padding: 'clamp(14px,2.2vw,30px)' }}>
      <header style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: '16px 28px',
        paddingBottom: 14, marginBottom: 'clamp(12px,1.6vw,20px)', borderBottom: '1px solid var(--grat-1)',
      }}>
        <div>
          <div className="eyebrow">{t.eyebrow}</div>
          <h1 style={{ fontSize: 'clamp(30px,5.2vw,54px)', margin: 0 }}>
            {t.titleA}<em>{t.titleEm}</em>{t.titleB}
          </h1>
        </div>
        <div className="num" style={{ marginLeft: 'auto', textAlign: 'right', fontSize: 11.5, lineHeight: 1.75, color: 'var(--muted)' }}>
          <b style={{ color: 'var(--parchment)', fontWeight: 500 }}>{b.place_label || '—'}</b> · {fmtLat(b.lat)} {fmtLon(b.lon)}<br />
          {b.local_clock.replace('T', ' ')} · {b.tz_used}<br />
          {b.utc_offset_used} · {core.house_system}
          {savedNote && (<><br /><span style={{ color: 'var(--brass)' }}>{t.saved}</span></>)}
        </div>
      </header>

      <div className="stage">
        <div>
          <div ref={wrapRef} style={{ position: 'relative', border: '1px solid var(--grat-2)', background: 'var(--shelf)', overflow: 'hidden' }}>
            <canvas ref={canvasRef} style={{ display: 'block', width: '100%', height: 'auto', cursor: 'crosshair', touchAction: 'none' }} />
            <div style={{
              position: 'absolute', left: 10, bottom: 8, fontFamily: 'var(--font-data)', fontSize: 10,
              letterSpacing: '.1em', color: 'var(--dim)', pointerEvents: 'none', textTransform: 'uppercase',
            }}>{t.hint}</div>
          </div>
          {/* legend — planet toggles */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 6px', marginTop: 12 }}>
            {PLANETS.map((p) => {
              const on = !hidden.has(p);
              return (
                <button key={p} type="button" onClick={() => toggle(p)} aria-pressed={on}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px 3px 6px', cursor: 'pointer',
                    border: '1px solid var(--grat-2)', fontSize: 11.5, color: 'var(--muted)',
                    fontFamily: 'var(--font-data)', letterSpacing: '.04em', background: 'none', opacity: on ? 1 : 0.32,
                  }}>
                  <span style={{ width: 13, height: 2, display: 'block', background: planetVar(p) }} />
                  <span>{PG[p]} {P_NAME[lang][p]}</span>
                </button>
              );
            })}
          </div>
        </div>

        <aside className="panel">
          <div className="panel-block">
            <div className="eyebrow" style={{ marginBottom: 9 }}>{t.point}</div>
            <div className="num" style={{ fontSize: 17, letterSpacing: '.02em', color: 'var(--parchment)' }}>
              {cursor ? `${fmtLat(cursor.lat)}  ${fmtLon(cursor.lon)}` : '—'}
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontStyle: 'italic', color: 'var(--brass)', marginTop: 3, minHeight: 24 }}>
              {cursor?.name || ''}
            </div>
          </div>

          <div className="panel-block">
            <div className="eyebrow" style={{ marginBottom: 9 }}>{t.anglesHere}</div>
            {timed ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '7px 12px' }}>
                {([['ASC', panel?.a.asc], ['MC', panel?.a.mc], ['DESC', panel?.a.desc], ['IC', panel?.a.ic]] as const).map(
                  ([nm, val]) => (
                    <div key={nm} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8, fontFamily: 'var(--font-data)', fontSize: 12 }}>
                      <span style={{ color: 'var(--dim)', letterSpacing: '.1em' }}>{nm}</span>
                      <span style={{ color: 'var(--parchment)' }}>{val === undefined ? '—' : fmtSign(val)}</span>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <div style={{ fontSize: 12.5, color: 'var(--brass)', fontFamily: 'var(--font-display)', fontStyle: 'italic', lineHeight: 1.45 }}>{t.noTime}</div>
            )}
          </div>

          <div className="panel-block">
            <div className="eyebrow" style={{ marginBottom: 9 }}>{t.onAngles}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 22 }}>
              {!timed ? (
                <div style={{ fontSize: 12, color: 'var(--dim)', fontStyle: 'italic', fontFamily: 'var(--font-display)' }}>{t.noTime}</div>
              ) : !panel ? (
                <div style={{ fontSize: 12, color: 'var(--dim)', fontStyle: 'italic', fontFamily: 'var(--font-display)' }}>{t.hoverPrompt}</div>
              ) : panel.contacts.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--dim)', fontStyle: 'italic', fontFamily: 'var(--font-display)' }}>{t.noneInOrb}</div>
              ) : (
                panel.contacts.map((c, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '16px 1fr auto auto', gap: 9, alignItems: 'baseline', fontSize: 12.5, fontFamily: 'var(--font-data)' }}>
                    <span style={{ fontSize: 14, textAlign: 'center', color: planetVar(c.body) }}>{PG[c.body]}</span>
                    <span style={{ fontFamily: 'var(--font-ui)', color: 'var(--parchment)' }}>{P_NAME[lang][c.body]}</span>
                    <span style={{ color: 'var(--dim)', letterSpacing: '.08em' }}>{c.angle.toUpperCase()}</span>
                    <span style={{ color: 'var(--brass)' }}>{c.orb.toFixed(2)}°</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="panel-block">
            <div className="eyebrow" style={{ marginBottom: 9 }}>{t.cities}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {CITIES.map(([n, la, lo]) => (
                <button key={n} type="button" onClick={() => setCursor({ lat: la, lon: lo, name: n })}
                  style={{ font: 'inherit', fontSize: 11.5, padding: '4px 9px', cursor: 'pointer', background: 'transparent', color: 'var(--muted)', border: '1px solid var(--grat-2)' }}>
                  {n}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={onSubmit} className="panel-block">
            <div className="eyebrow" style={{ marginBottom: 9 }}>{t.yourData}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Field label={t.date}><input type="date" value={bdate} onChange={(e) => setBdate(e.target.value)} style={inp} /></Field>
              <Field label={t.time}><input type="time" value={btime} onChange={(e) => setBtime(e.target.value)} style={inp} /></Field>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 7 }}>
              <Field label={t.lat}><input type="number" step="0.0001" value={blat} onChange={(e) => setBlat(e.target.value)} style={inp} /></Field>
              <Field label={t.lon}><input type="number" step="0.0001" value={blon} onChange={(e) => setBlon(e.target.value)} style={inp} /></Field>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 7 }}>
              <Field label={t.place}><input type="text" value={bplace} onChange={(e) => setBplace(e.target.value)} style={inp} /></Field>
              <Field label={t.tz}>
                <select value={btz} onChange={(e) => setBtz(e.target.value)} style={inp}>
                  {['Europe/Kyiv', 'Europe/Moscow', 'Europe/Prague', 'Europe/Madrid', 'Asia/Tokyo', 'UTC'].map((z) => (
                    <option key={z} value={z}>{z}</option>
                  ))}
                </select>
              </Field>
            </div>
            <button type="submit" disabled={busy} style={{
              marginTop: 10, width: '100%', background: 'var(--brass)', color: 'var(--abyss)', border: 0,
              fontFamily: 'var(--font-ui)', fontWeight: 600, padding: 8, cursor: busy ? 'not-allowed' : 'pointer',
              letterSpacing: '.02em', opacity: busy ? 0.45 : 1,
            }}>{busy ? t.building : t.build}</button>
            {notice && (
              <div style={{ border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)', color: 'var(--notice-ink)', padding: '8px 10px', fontSize: 12, lineHeight: 1.5, marginTop: 9 }}>
                {notice.text}{notice.resetAt ? ` ${t.resetAt}${notice.resetAt}.` : ''}
                {notice.accountUrl && <> <a href={notice.accountUrl} style={{ color: 'var(--brass)' }}>{t.account}</a></>}
              </div>
            )}
          </form>
        </aside>
      </div>

      <div className="provenance" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 26px' }}>
        {prov ? (
          <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.engine}</b> {prov.ephemeris_engine} {prov.ephemeris_version}</span>
        ) : (
          <>
            <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.engine}</b> Swiss Ephemeris (SWIEPH)</span>
            <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.data}</b> {t.demo}</span>
          </>
        )}
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.houses}</b> {core.house_system}</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.lines}</b> {lines.length}</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>GMST</b> {core.gmst.toFixed(4)}°</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>{t.tilt}</b> {core.obliquity.toFixed(5)}°</span>
        <span><b style={{ color: 'var(--muted)', fontWeight: 400 }}>JD_UT</b> {core.jd_ut}</span>
      </div>

      <p style={{ fontSize: 13, color: 'var(--muted)', maxWidth: '64ch', lineHeight: 1.6, marginTop: 12 }}>
        <b style={{ color: 'var(--parchment)', fontWeight: 500 }}>{t.disclaimerLead}</b> {t.disclaimer}
      </p>
    </main>
  );
}

const inp: React.CSSProperties = {
  width: '100%', background: 'var(--abyss)', color: 'var(--parchment)',
  border: '1px solid var(--grat-2)', fontFamily: 'var(--font-data)', fontSize: 12, padding: '6px 8px',
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ flex: 1, minWidth: 110 }}>
      <label style={{ display: 'block', color: 'var(--dim)', fontFamily: 'var(--font-data)', fontSize: 10, letterSpacing: '.04em', textTransform: 'uppercase', margin: '0 0 3px' }}>{label}</label>
      {children}
    </div>
  );
}
