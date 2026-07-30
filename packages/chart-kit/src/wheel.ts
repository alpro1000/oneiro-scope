/**
 * The natal wheel, as geometry rather than as pixels.
 *
 * `wheelLayout` returns plain numbers — ring radii, cusp spokes, glyph
 * positions, aspect chords — and `wheelSvg` turns those into a
 * self-contained SVG string. The split is what lets the layout be
 * tested: "no two glyphs overlap" and "cusp 1 points at the Ascendant"
 * are assertions about numbers, not about a rendered image.
 *
 * Everything here is a pure function of a `chart_core` plus a location,
 * like the rest of the kit: the wheel for ANY place on Earth costs
 * nothing and needs no network, which is the whole point of the thin
 * core.
 *
 * ORIENTATION. Astrological wheels put the Ascendant on the left,
 * horizon horizontal, and run counter-clockwise in zodiacal order —
 * which is neither SVG's coordinate system (y grows downward) nor its
 * angle convention. `pointAt` is the single place that conversion
 * happens; everything else works in ecliptic longitude.
 *
 * NO BIRTH TIME, NO WHEEL. When `birth.time_known` is false the chart
 * was computed for noon and the angles are meaningless, so the layout
 * refuses rather than drawing twelve houses that mean nothing
 * (conventions.md §12).
 */

import type { Aspect, ChartCore, HouseSystem } from './types';
import { angles, houseCusps, norm360, resolveSystemFor, sep180 } from './angles';
import { aspects } from './aspects';

export interface WheelPoint {
  x: number;
  y: number;
}

export interface WheelGlyph {
  body: string;
  /** True ecliptic longitude — what the chart means. */
  longitude: number;
  /**
   * Longitude the glyph is DRAWN at. Equal to `longitude` unless
   * neighbours were too close to read, in which case they were spread.
   */
  drawnAt: number;
  retrograde: boolean;
  at: WheelPoint;
  /** Where the tick joining glyph to true position starts and ends. */
  tick: [WheelPoint, WheelPoint];
}

export interface WheelSpoke {
  /** 1–12 for cusps; the four angles are marked separately. */
  house: number;
  longitude: number;
  from: WheelPoint;
  to: WheelPoint;
  /** Cusps 1, 4, 7 and 10 are the angles and are drawn heavier. */
  isAngle: boolean;
}

export interface WheelAspect extends Aspect {
  from: WheelPoint;
  to: WheelPoint;
}

export interface WheelLayout {
  size: number;
  center: WheelPoint;
  /** Outer, zodiac-band inner, glyph ring, aspect-chord ring. */
  radii: { outer: number; zodiac: number; glyphs: number; aspects: number };
  system: HouseSystem;
  /** True when the system had to be substituted at THIS location. */
  substituted: boolean;
  asc: number;
  mc: number;
  spokes: WheelSpoke[];
  glyphs: WheelGlyph[];
  chords: WheelAspect[];
  /** Sign boundaries, as longitudes; the renderer draws the band ticks. */
  signTicks: number[];
}

export interface WheelOptions {
  /** Pixel size of the square viewport. */
  size?: number;
  /** House system override; by default the one usable at this location. */
  system?: HouseSystem;
  /** Minimum angular gap between drawn glyphs, degrees. */
  minGlyphGap?: number;
  /** Bodies to draw; defaults to every body in the core. */
  bodies?: string[];
}

const DEFAULTS = { size: 640, minGlyphGap: 6 };

/**
 * Ecliptic longitude → screen point.
 *
 * Pinned by the four places a wheel must put its angles, with d = λ − Asc:
 *
 *     d =   0° → (cx − r, cy)   Ascendant, 9 o'clock
 *     d =  90° → (cx, cy + r)   IC,        6 o'clock
 *     d = 180° → (cx + r, cy)   Descendant, 3 o'clock
 *     d = 270° → (cx, cy − r)   MC,        12 o'clock
 *
 * which is x = cx − r·cos d, y = cy + r·sin d. Note the PLUS on y: SVG's
 * axis points down, and that is what makes screen-clockwise read as the
 * counter-clockwise wheel astrologers expect. Getting this sign wrong
 * mirrors the chart — houses run backwards and the MC lands at the
 * bottom — while every number in the layout stays correct, so the four
 * cases above are asserted in `wheel.test.ts` rather than trusted.
 */
function pointAt(
  center: WheelPoint,
  radius: number,
  longitude: number,
  asc: number,
): WheelPoint {
  const d = ((longitude - asc) * Math.PI) / 180;
  return {
    x: center.x - radius * Math.cos(d),
    y: center.y + radius * Math.sin(d),
  };
}

/**
 * Spread glyphs that would otherwise overlap.
 *
 * Stelliums are the normal case, not the edge case — four bodies inside
 * two degrees is an ordinary chart, and drawn honestly they become one
 * illegible smudge. Each cluster is spread evenly around its own mean so
 * the group still reads as a group, and every glyph keeps a tick back to
 * where it truly is, so the displacement is visible rather than a quiet
 * lie about position.
 */
function spread(
  bodies: Array<{ body: string; longitude: number }>,
  minGap: number,
): Map<string, number> {
  const n = bodies.length;
  const drawn = new Map<string, number>();
  if (n === 0) return drawn;
  if (n * minGap > 360) {
    // No arrangement satisfies the gap. Quietly returning overlapping
    // glyphs would be the silent degradation the project bans, and an
    // even distribution would lie about position, so refuse.
    throw new Error(
      `${n} bodies cannot be drawn ${minGap}° apart on a 360° wheel; ` +
        `reduce minGlyphGap below ${(360 / n).toFixed(2)}°`,
    );
  }

  // Put the seam in the widest empty stretch of sky, so the wrap-around
  // is the one place no cluster needs to straddle. Everything below can
  // then work on a plain line.
  const sorted = [...bodies].sort((a, b) => a.longitude - b.longitude);
  let widest = 0;
  let seamAfter = n - 1;
  for (let i = 0; i < n; i++) {
    const gap = norm360(sorted[(i + 1) % n].longitude - sorted[i].longitude);
    if (gap > widest) {
      widest = gap;
      seamAfter = i;
    }
  }
  const origin = sorted[(seamAfter + 1) % n].longitude;
  const line = sorted
    .map((b) => ({ body: b.body, u: norm360(b.longitude - origin) }))
    .sort((a, b) => a.u - b.u);

  // Merge to a fixed point. One greedy pass is not enough: spreading a
  // cluster widens it, and the widened edge can collide with a body that
  // was comfortably clear of the original. Repeat until nothing moves.
  let groups = line.map((b) => ({ members: [b.body], count: 1, mean: b.u }));
  for (let guard = 0; guard <= n; guard++) {
    const merged: typeof groups = [];
    let changed = false;
    for (const g of groups) {
      const prev = merged[merged.length - 1];
      if (prev) {
        const prevEnd = prev.mean + ((prev.count - 1) * minGap) / 2;
        const gStart = g.mean - ((g.count - 1) * minGap) / 2;
        if (gStart - prevEnd < minGap - 1e-9) {
          const total = prev.count + g.count;
          // Weighted mean of group means is the true mean of all their
          // members, since each group mean already averages its own.
          prev.mean = (prev.mean * prev.count + g.mean * g.count) / total;
          prev.count = total;
          prev.members.push(...g.members);
          changed = true;
          continue;
        }
      }
      merged.push({ ...g, members: [...g.members] });
    }
    groups = merged;
    if (!changed) break;
  }

  for (const g of groups) {
    const start = g.mean - ((g.count - 1) * minGap) / 2;
    g.members.forEach((body, k) => {
      drawn.set(body, norm360(origin + start + k * minGap));
    });
  }
  return drawn;
}

export function wheelLayout(
  core: ChartCore,
  lat: number,
  lon: number,
  opts: WheelOptions = {},
): WheelLayout {
  if (!core.birth.time_known) {
    throw new Error(
      'this chart has no birth time: it was computed for noon, so the ' +
        'Ascendant, Midheaven and every house cusp are arbitrary. A wheel ' +
        'drawn from them would look exactly as authoritative as a real one.',
    );
  }

  const size = opts.size ?? DEFAULTS.size;
  const minGap = opts.minGlyphGap ?? DEFAULTS.minGlyphGap;
  const center = { x: size / 2, y: size / 2 };
  const outer = size * 0.47;
  const radii = {
    outer,
    zodiac: outer * 0.86,
    glyphs: outer * 0.74,
    aspects: outer * 0.6,
  };

  const resolved = resolveSystemFor(core, lat, lon);
  const system = opts.system ?? resolved.system;
  const { asc, mc } = angles(core, lat, lon);
  const cusps = houseCusps(core, lat, lon, system);

  const spokes: WheelSpoke[] = cusps.map((longitude, i) => ({
    house: i + 1,
    longitude,
    from: pointAt(center, radii.aspects, longitude, asc),
    to: pointAt(center, radii.zodiac, longitude, asc),
    isAngle: i === 0 || i === 3 || i === 6 || i === 9,
  }));

  const names = opts.bodies ?? Object.keys(core.bodies);
  const sorted = names
    .map((body) => ({ body, longitude: core.bodies[body].ecl_lon }))
    .sort((a, b) => a.longitude - b.longitude);
  const drawnAt = spread(sorted, minGap);

  const glyphs: WheelGlyph[] = sorted.map(({ body, longitude }) => {
    const shown = drawnAt.get(body)!;
    return {
      body,
      longitude,
      drawnAt: shown,
      retrograde: core.bodies[body].retrograde,
      at: pointAt(center, radii.glyphs, shown, asc),
      tick: [
        pointAt(center, radii.zodiac, longitude, asc),
        pointAt(center, radii.zodiac * 0.96, longitude, asc),
      ],
    };
  });

  const chords: WheelAspect[] = aspects(core)
    .filter((a) => names.includes(a.a) && names.includes(a.b))
    .map((a) => ({
      ...a,
      from: pointAt(center, radii.aspects, core.bodies[a.a].ecl_lon, asc),
      to: pointAt(center, radii.aspects, core.bodies[a.b].ecl_lon, asc),
    }));

  return {
    size,
    center,
    radii,
    system,
    substituted: opts.system ? false : resolved.substituted,
    asc,
    mc,
    spokes,
    glyphs,
    chords,
    signTicks: Array.from({ length: 12 }, (_, i) => i * 30),
  };
}

/** Glyphs, so the SVG needs no font beyond the system's own. */
const GLYPH: Record<string, string> = {
  Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂',
  Jupiter: '♃', Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇',
  TrueNode: '☊', Chiron: '⚷',
};

const ASPECT_COLOUR: Record<string, string> = {
  conjunction: '#b9a7ff',
  opposition: '#ff8686',
  square: '#ff8686',
  trine: '#77d8a8',
  sextile: '#77d8a8',
  quincunx: '#c9a06a',
};

const esc = (s: string): string =>
  s.replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!,
  );

const n2 = (v: number): string => v.toFixed(2);

/**
 * A complete, standalone SVG for the wheel.
 *
 * Deliberately string-based rather than DOM-based: the same function
 * serves the static PWA page, a React component and a server-side
 * render, and it stays testable without a browser.
 */
export function wheelSvg(layout: WheelLayout): string {
  const { center: c, radii, asc } = layout;
  const parts: string[] = [];

  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${layout.size} ${layout.size}" ` +
      `width="100%" role="img" aria-label="Natal wheel">`,
    `<circle cx="${n2(c.x)}" cy="${n2(c.y)}" r="${n2(radii.outer)}" fill="none" stroke="currentColor" stroke-opacity=".45"/>`,
    `<circle cx="${n2(c.x)}" cy="${n2(c.y)}" r="${n2(radii.zodiac)}" fill="none" stroke="currentColor" stroke-opacity=".25"/>`,
    `<circle cx="${n2(c.x)}" cy="${n2(c.y)}" r="${n2(radii.aspects)}" fill="none" stroke="currentColor" stroke-opacity=".15"/>`,
  );

  for (const tick of layout.signTicks) {
    const a = pointAt(c, radii.zodiac, tick, asc);
    const b = pointAt(c, radii.outer, tick, asc);
    parts.push(
      `<line x1="${n2(a.x)}" y1="${n2(a.y)}" x2="${n2(b.x)}" y2="${n2(b.y)}" stroke="currentColor" stroke-opacity=".35"/>`,
    );
  }

  for (const ch of layout.chords) {
    parts.push(
      `<line x1="${n2(ch.from.x)}" y1="${n2(ch.from.y)}" x2="${n2(ch.to.x)}" y2="${n2(ch.to.y)}" ` +
        `stroke="${ASPECT_COLOUR[ch.type] ?? '#888'}" stroke-opacity="${ch.applying ? '.85' : '.4'}" ` +
        `stroke-width="${ch.type === 'conjunction' ? 1.4 : 1}"/>`,
    );
  }

  for (const s of layout.spokes) {
    parts.push(
      `<line x1="${n2(s.from.x)}" y1="${n2(s.from.y)}" x2="${n2(s.to.x)}" y2="${n2(s.to.y)}" ` +
        `stroke="currentColor" stroke-opacity="${s.isAngle ? '.8' : '.3'}" ` +
        `stroke-width="${s.isAngle ? 1.8 : 1}"/>`,
    );
  }

  for (const g of layout.glyphs) {
    parts.push(
      `<line x1="${n2(g.tick[0].x)}" y1="${n2(g.tick[0].y)}" x2="${n2(g.tick[1].x)}" y2="${n2(g.tick[1].y)}" stroke="currentColor" stroke-opacity=".5"/>`,
      `<text x="${n2(g.at.x)}" y="${n2(g.at.y)}" text-anchor="middle" dominant-baseline="central" ` +
        `font-size="${n2(layout.size * 0.032)}" fill="currentColor">${esc(GLYPH[g.body] ?? g.body)}` +
        `${g.retrograde ? '<tspan font-size="60%" dy="-0.6em">℞</tspan>' : ''}</text>`,
    );
  }

  parts.push('</svg>');
  return parts.join('');
}
