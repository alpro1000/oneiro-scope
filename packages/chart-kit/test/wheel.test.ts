/**
 * The wheel and the lunar day, both derived from a core alone.
 *
 * The lunar assertions are golden ones — the fixture is produced by the
 * server's OWN `backend/services/lunar/engine.py` helpers, so this is a
 * client-vs-server check like the rest of the set, not a restatement of
 * the kit's arithmetic.
 *
 * The wheel assertions are structural. A rendered wheel is easy to
 * eyeball and hard to test, which is exactly why the layout returns
 * numbers: "cusp 1 points at the Ascendant" and "no two glyphs are
 * closer than the minimum gap" are checkable, and a wheel that satisfies
 * them cannot be silently wrong in the ways that matter.
 */

import { describe, expect, it } from 'vitest';

import golden from './golden.json';
import {
  angles,
  houseCusps,
  lunarDay,
  norm360,
  phaseOf,
  sep180,
  signOf,
  wheelLayout,
  wheelSvg,
} from '../src/index';
import type { ChartCore } from '../src/types';

const charts = golden.charts as unknown as Array<{
  label: string;
  chart_core: ChartCore;
  expected: {
    asc: number;
    mc: number;
    lunar: {
      phase_angle: number;
      moon_age_days: number;
      lunar_day: number;
      phase: string;
      moon_sign: string;
    };
  };
}>;

const diff = (a: number, b: number): number => Math.abs(sep180(a, b));
const timed = charts.filter((c) => c.chart_core.birth.time_known);

describe.each(charts)('lunar day — $label', (chart) => {
  const got = lunarDay(chart.chart_core);
  const want = chart.expected.lunar;

  it('matches the server exactly, not approximately', () => {
    // Same formula, same constant: anything but an exact match on the
    // integer day means the two have drifted.
    expect(got.lunarDay).toBe(want.lunar_day);
    expect(got.phase).toBe(want.phase);
    expect(got.phaseAngle).toBeCloseTo(want.phase_angle, 4);
    expect(got.moonAgeDays).toBeCloseTo(want.moon_age_days, 4);
  });

  it('names the Moon’s sign the same body the server does', () => {
    // The kit speaks lowercase throughout (signOf, dignities); the server
    // capitalises. One vocabulary inside the kit beats matching the
    // server's casing, so the comparison is case-insensitive on purpose.
    expect(got.moonSign).toBe(want.moon_sign.toLowerCase());
  });

  it('refuses to invent an illuminated fraction', () => {
    // The server reads it from swe.pheno_ut. The only formula derivable
    // from two longitudes is (1-cos)/2, which WP-16 removed for being
    // wrong by up to ~4pp — so the kit must not offer one at all.
    expect(got.illuminationKnown).toBe(false);
    expect(Object.keys(got)).not.toContain('illumination');
  });
});

describe('phase boundaries follow the server’s eight-way split', () => {
  it.each([
    [0, 'new_moon'], [22.4, 'new_moon'], [22.5, 'waxing_crescent'],
    [67.5, 'first_quarter'], [112.5, 'waxing_gibbous'],
    [157.5, 'full_moon'], [202.5, 'waning_gibbous'],
    [247.5, 'last_quarter'], [292.5, 'waning_crescent'],
    [337.5, 'new_moon'], [359.9, 'new_moon'],
  ])('%s° is %s', (angle, expected) => {
    expect(phaseOf(angle)).toBe(expected);
  });
});

describe('a chart with no birth time', () => {
  const untimed = charts.find((c) => !c.chart_core.birth.time_known)!;

  it('is in the golden set at all', () => {
    expect(untimed).toBeDefined();
  });

  it('still has a lunar day — that needs no angles', () => {
    expect(lunarDay(untimed.chart_core).lunarDay).toBeGreaterThan(0);
  });

  it('refuses to produce a wheel', () => {
    // Noon was assumed so the slow bodies have positions. The Ascendant
    // and every cusp are then arbitrary, and a drawn wheel would look
    // exactly as authoritative as a real one.
    expect(() =>
      wheelLayout(untimed.chart_core, 51.5, -0.1),
    ).toThrow(/no birth time/i);
  });
});

describe.each(timed)('wheel layout — $label', (chart) => {
  const core = chart.chart_core;
  const { lat, lon } = core.birth;
  const layout = wheelLayout(core, lat, lon);

  it('puts cusp 1 on the Ascendant and cusp 10 on the MC', () => {
    const a = angles(core, lat, lon);
    if (layout.system === 'whole_sign') return;
    expect(diff(layout.spokes[0].longitude, a.asc)).toBeLessThan(0.01);
    expect(diff(layout.spokes[9].longitude, a.mc)).toBeLessThan(0.01);
  });

  it('marks exactly the four angular cusps as angles', () => {
    expect(layout.spokes.filter((s) => s.isAngle).map((s) => s.house))
      .toEqual([1, 4, 7, 10]);
  });

  it('puts the four angles where a wheel puts them', () => {
    // The orientation the whole layout rests on, and the one thing that
    // can be wrong while every number stays right: flip the sine and the
    // chart mirrors — houses run backwards, MC lands at the bottom.
    // Asc at 9 o'clock, IC at 6, Desc at 3, MC at 12.
    const a = angles(core, lat, lon);
    const r = layout.radii.zodiac;
    const at = (lon0: number) => {
      const d = ((lon0 - a.asc) * Math.PI) / 180;
      return {
        x: layout.center.x - r * Math.cos(d),
        y: layout.center.y + r * Math.sin(d),
      };
    };
    expect(at(a.asc).x).toBeCloseTo(layout.center.x - r, 6);
    expect(at(a.asc).y).toBeCloseTo(layout.center.y, 6);
    expect(at(norm360(a.asc + 90)).y).toBeCloseTo(layout.center.y + r, 6);
    expect(at(a.desc).x).toBeCloseTo(layout.center.x + r, 6);
    // And the MC, wherever it falls in longitude, must be in the upper
    // half: that is what "counter-clockwise from the eastern horizon"
    // means once the Ascendant is pinned to the left.
    const mc = layout.spokes[9];
    if (layout.system !== 'whole_sign') {
      expect(mc.to.y).toBeLessThan(layout.center.y);
    }
  });

  it('places every body and keeps drawn glyphs legible', () => {
    expect(layout.glyphs.map((g) => g.body).sort())
      .toEqual(Object.keys(core.bodies).sort());
    const drawn = layout.glyphs.map((g) => g.drawnAt).sort((a, b) => a - b);
    for (let i = 1; i < drawn.length; i++) {
      // 6° default gap, minus a hair for floating point.
      expect(
        Math.abs(sep180(drawn[i], drawn[i - 1])),
        `${layout.glyphs[i].body} too close to its neighbour`,
      ).toBeGreaterThan(5.99);
    }
  });

  it('never moves a glyph far enough to change its sign silently', () => {
    // Spreading a stellium is a drawing decision; it must not become a
    // claim about position. Each glyph keeps a tick back to the truth,
    // and the displacement stays small.
    for (const g of layout.glyphs) {
      expect(Math.abs(sep180(g.drawnAt, g.longitude))).toBeLessThan(20);
      expect(signOf(g.longitude)).toBe(signOf(g.longitude));
    }
  });

  it('reports the substitution when the birth latitude forced one', () => {
    const polar = Math.abs(lat) >= 90 - core.obliquity;
    expect(layout.substituted).toBe(polar);
    expect(layout.system).toBe(polar ? 'porphyry' : 'placidus');
  });

  it('draws only aspects between bodies it drew', () => {
    const shown = new Set(layout.glyphs.map((g) => g.body));
    for (const c of layout.chords) {
      expect(shown.has(c.a) && shown.has(c.b)).toBe(true);
    }
  });
});

describe('the SVG the layout produces', () => {
  const chart = timed[0];
  const { lat, lon } = chart.chart_core.birth;
  const svg = wheelSvg(wheelLayout(chart.chart_core, lat, lon));

  it('is a single self-contained element', () => {
    expect(svg.startsWith('<svg')).toBe(true);
    expect(svg.endsWith('</svg>')).toBe(true);
    expect(svg).toContain('xmlns="http://www.w3.org/2000/svg"');
  });

  it('references nothing off-device', () => {
    // A wheel that reaches for a CDN font or an external image is a wheel
    // that breaks offline — which is the one thing the thin core exists
    // to prevent.
    expect(svg).not.toMatch(/https?:\/\/(?!www\.w3\.org)/);
    expect(svg).not.toMatch(/<image|@import|url\(/);
  });

  it('carries every body and marks retrogrades', () => {
    const layout = wheelLayout(chart.chart_core, lat, lon);
    expect((svg.match(/<text /g) ?? []).length).toBe(layout.glyphs.length);
    const retro = layout.glyphs.filter((g) => g.retrograde).length;
    expect((svg.match(/℞/g) ?? []).length).toBe(retro);
  });

  it('produces the same string twice — no clock, no randomness', () => {
    expect(wheelSvg(wheelLayout(chart.chart_core, lat, lon))).toBe(svg);
  });

  it('escapes anything that could close a tag', () => {
    const hostile: ChartCore = {
      ...chart.chart_core,
      bodies: { '</svg><script>x</script>': chart.chart_core.bodies.Sun },
    };
    const out = wheelSvg(wheelLayout(hostile, lat, lon));
    expect(out).not.toContain('<script>');
    expect((out.match(/<\/svg>/g) ?? []).length).toBe(1);
  });
});

describe('relocation redraws the wheel', () => {
  const chart = timed.find((c) => Math.abs(c.chart_core.birth.lat) < 60)!;

  it('gives a different Ascendant at a different place', () => {
    const home = wheelLayout(chart.chart_core, chart.chart_core.birth.lat,
                             chart.chart_core.birth.lon);
    const away = wheelLayout(chart.chart_core, -33.8688, 151.2093);
    expect(diff(home.asc, away.asc)).toBeGreaterThan(1);
  });

  it('substitutes the house system poleward instead of throwing', () => {
    const arctic = wheelLayout(chart.chart_core, 78.2232, 15.6469);
    expect(arctic.system).toBe('porphyry');
    expect(arctic.substituted).toBe(true);
    expect(arctic.spokes).toHaveLength(12);
    expect(diff(arctic.spokes[0].longitude, arctic.asc)).toBeLessThan(0.01);
  });

  it('agrees with houseCusps, which the golden set already pins', () => {
    const cusps = houseCusps(chart.chart_core, 40.7128, -74.006);
    const layout = wheelLayout(chart.chart_core, 40.7128, -74.006);
    expect(layout.spokes.map((s) => s.longitude)).toEqual(cusps);
  });
});
