/**
 * Astrocartography map — an MCP App view for `astrocartography_lines`.
 *
 * The strongest module the competition does not offer, drawn where the
 * conversation is. `astrocartography_lines` already returns the line set as
 * GeoJSON, so this view draws what the server computed rather than
 * recomputing it — two implementations of one formula always drift, and the
 * one the user is looking at must be the one the server would defend.
 *
 * SVG rather than canvas: it scales to whatever width the host gives the
 * iframe, prints, and needs no resize redraw. Equirectangular, like the
 * reference chart — nautical, not a tile service, and no tile service means
 * no network.
 */

import type { ToolResult } from './bridge';
// The Next app's coastline data, imported rather than copied: two copies of
// static geography drift the moment one is edited, and nothing would catch
// it. Aliased to frontend/lib/world-coast.ts in both tsconfig and the build.
import { WORLD_COAST } from '@frontend/world-coast';
import { esc, fromResult, mountView, type Lang } from './view';

// Bodies get the classical-metal colours; the tokens carry them as --p-*.
const P_GLYPH: Record<string, string> = {
  Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂', Jupiter: '♃',
  Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇',
};

// Latitude window of the reference basemap: past these the equirectangular
// projection stretches into uselessness.
const LAT_TOP = 78;
const LAT_BOTTOM = -58;

const COPY = {
  ru: {
    title: 'Астрокартография',
    lede: 'Линии — места, где планета стоит на одном из углов карты.',
    legend: 'Линии',
    mc: 'MC — меридиан, кульминация', ic: 'IC — надир',
    ac: 'Asc — восход', dc: 'Desc — заход',
    birth: 'Место рождения',
    lines: 'линий',
    method: 'метод',
    waiting: 'Ожидание линий от сервера…',
    empty: 'Нет данных карты. Вызовите astrocartography_lines.',
    disclaimerLead: 'Линии и углы — геометрия, она проверяема.',
    disclaimer: 'Символическое значение планеты на угле — традиция толкования, '
      + 'а не прогноз. Рефлексивно-развлекательный материал, не медицинский, '
      + 'психологический, юридический или финансовый совет.',
  },
  en: {
    title: 'Astrocartography',
    lede: 'A line marks where a planet sits on one of the chart angles.',
    legend: 'Lines',
    mc: 'MC — meridian, culmination', ic: 'IC — nadir',
    ac: 'Asc — rising', dc: 'Desc — setting',
    birth: 'Birth place',
    lines: 'lines',
    method: 'method',
    waiting: 'Waiting for the lines…',
    empty: 'No map data. Call astrocartography_lines.',
    disclaimerLead: 'Lines and angles are geometry — verifiable.',
    disclaimer: 'The symbolic meaning of a planet on an angle is a tradition of '
      + 'interpretation, not a prediction. Reflective / entertainment material, '
      + 'not medical, psychological, legal or financial advice.',
  },
} as const;

interface Feature {
  properties?: { planet?: string; angle?: string };
  geometry?: { type?: string; coordinates?: number[][] };
}

interface Payload {
  lines?: { features?: Feature[] };
  chart?: { birth?: { lat?: number; lon?: number; name?: string } };
  methodology?: string;
  meta?: Record<string, unknown>;
  locale?: string;
}

const W = 1000;
const H = Math.round((W * (LAT_TOP - LAT_BOTTOM)) / 360);
const px = (lon: number) => ((lon + 180) / 360) * W;
const py = (lat: number) => ((LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM)) * H;
const n2 = (v: number) => Math.round(v * 100) / 100;

/** MC/IC are meridians (solid/dashed); Asc/Desc are horizon curves. */
function dashFor(angle: string): string {
  if (angle === 'IC') return ' stroke-dasharray="5 4"';
  if (angle === 'DC' || angle === 'Desc') return ' stroke-dasharray="2 4"';
  return '';
}

/**
 * A polyline, split where it wraps the antimeridian.
 *
 * Without the split a curve leaving at +180° draws a straight line all the way
 * back across the map — a line through places the planet is nowhere near.
 */
function pathFor(coords: number[][]): string[] {
  const runs: string[][] = [];
  let run: string[] = [];
  let prevLon: number | null = null;
  for (const [lon, lat] of coords) {
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    if (lat > LAT_TOP || lat < LAT_BOTTOM) continue;
    if (prevLon !== null && Math.abs(lon - prevLon) > 180) {
      if (run.length > 1) runs.push(run);
      run = [];
    }
    run.push(`${n2(px(lon))},${n2(py(lat))}`);
    prevLon = lon;
  }
  if (run.length > 1) runs.push(run);
  return runs.map((r) => r.join(' '));
}

function render(payload: Payload, lang: Lang): string {
  const t = COPY[lang];
  const features = payload.lines?.features ?? [];

  const land = WORLD_COAST.map((poly) => {
    const pts = poly
      .filter(([, lat]) => lat <= LAT_TOP && lat >= LAT_BOTTOM)
      .map(([lon, lat]) => `${n2(px(lon))},${n2(py(lat))}`)
      .join(' ');
    return pts
      ? `<polygon points="${pts}" fill="var(--land)" stroke="var(--land-edge)" stroke-width="0.7"/>`
      : '';
  }).join('');

  const graticule: string[] = [];
  for (let lon = -180; lon <= 180; lon += 30) {
    graticule.push(
      `<line x1="${n2(px(lon))}" y1="0" x2="${n2(px(lon))}" y2="${H}" `
      + `stroke="${lon === 0 ? 'var(--land-edge)' : 'var(--grat-1)'}" stroke-width="0.7"/>`,
    );
  }
  for (let lat = -40; lat <= 70; lat += 20) {
    graticule.push(
      `<line x1="0" y1="${n2(py(lat))}" x2="${W}" y2="${n2(py(lat))}" `
      + `stroke="${lat === 0 ? 'var(--land-edge)' : 'var(--grat-1)'}" stroke-width="0.7"/>`,
    );
  }

  const drawn: string[] = [];
  const present = new Set<string>();
  for (const f of features) {
    const planet = f.properties?.planet ?? '';
    const angle = f.properties?.angle ?? '';
    const coords = f.geometry?.coordinates;
    if (!Array.isArray(coords)) continue;
    present.add(planet);
    const colour = `var(--p-${planet.toLowerCase()},var(--muted))`;
    for (const pts of pathFor(coords)) {
      drawn.push(
        `<polyline points="${pts}" fill="none" stroke="${colour}" `
        + `stroke-width="1.1" stroke-opacity=".85"${dashFor(angle)}>`
        + `<title>${esc(planet)} ${esc(angle)}</title></polyline>`,
      );
    }
  }

  const birth = payload.chart?.birth;
  const mark = birth && Number.isFinite(birth.lat) && Number.isFinite(birth.lon)
    ? `<g><circle cx="${n2(px(birth.lon!))}" cy="${n2(py(birth.lat!))}" r="4" `
      + `fill="none" stroke="var(--brass)" stroke-width="1.4"/>`
      + `<circle cx="${n2(px(birth.lon!))}" cy="${n2(py(birth.lat!))}" r="1.4" fill="var(--brass)"/></g>`
    : '';

  const legend = [...present].sort().map((p) =>
    `<span class="lg"><i style="background:var(--p-${p.toLowerCase()},var(--muted))"></i>`
    + `${P_GLYPH[p] ?? ''} ${esc(p)}</span>`).join('');

  const meta = payload.meta ?? {};
  const provBits = [
    payload.methodology ? `<span><b>${t.method}</b> ${esc(payload.methodology)}</span>` : '',
    `<span><b>${t.lines}</b> ${features.length}</span>`,
    meta.request_id ? `<span><b>request</b> ${esc(String(meta.request_id))}</span>` : '',
  ].filter(Boolean).join('');

  return `
    <div class="head">
      <div class="eyebrow">Astro · Carto · Graphy · Lewis 1976</div>
      <h1>${t.title}</h1>
      <p class="lede">${t.lede}</p>
    </div>
    <svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${t.title}">
      <rect width="${W}" height="${H}" fill="var(--abyss)"/>
      ${graticule.join('')}
      ${land}
      ${drawn.join('')}
      ${mark}
    </svg>
    <div class="legend">
      <div class="eyebrow">${t.legend}</div>
      <div class="lgs">${legend}</div>
      <div class="kinds">
        <span><i class="k solid"></i>${t.mc}</span>
        <span><i class="k dashed"></i>${t.ic}</span>
        <span><i class="k solid"></i>${t.ac}</span>
        <span><i class="k dotted"></i>${t.dc}</span>
      </div>
      ${birth?.name ? `<div class="kv"><span>${t.birth}</span><b>${esc(birth.name)}</b></div>` : ''}
    </div>
    <div class="prov">${provBits}</div>
    <p class="disclaimer"><b>${t.disclaimerLead}</b> ${t.disclaimer}</p>
  `;
}

mountView<Payload>({
  pick: (result: ToolResult) =>
    fromResult<Payload>(result, (c) =>
      (c as Payload).lines?.features ? (c as Payload) : null),
  render,
  strings: {
    ru: { waiting: COPY.ru.waiting, empty: COPY.ru.empty },
    en: { waiting: COPY.en.waiting, empty: COPY.en.empty },
  },
});
