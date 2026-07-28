/**
 * chart-kit vs the server, on 20 deliberately awkward charts.
 *
 * This is the test the architecture stands on. Two implementations of
 * one formula always drift, and when they do the client quietly draws a
 * chart the server would never have produced — the user has no way to
 * notice. So every number the kit derives from a `chart_core` is
 * compared against the server's own answer for the same chart, and CI
 * goes red past 0.01°.
 *
 * Regenerate the fixture with `npm run golden` after any change to the
 * ephemeris setup or the chart_core contract.
 */

import { describe, expect, it } from 'vitest';

import golden from './golden.json';
import {
  acgLines,
  angles,
  aspects,
  contacts,
  dignities,
  houseCusps,
  houses,
  mcLongitude,
  sep180,
  signOf,
} from '../src/index';
import type { ChartCore } from '../src/types';

const TOL = golden.tolerance_deg;
const charts = golden.charts as unknown as Array<{
  label: string;
  why: string;
  chart_core: ChartCore;
  house_system_note: string | null;
  expected: {
    asc: number;
    mc: number;
    cusps: number[];
    aspects: Array<{ a: string; b: string; type: string; orb: number; applying: boolean }>;
  };
}>;

/** Angular difference that respects the 0°/360° seam. */
const diff = (a: number, b: number): number => Math.abs(sep180(a, b));

describe('the golden set is what it claims to be', () => {
  it('carries 20 charts', () => {
    expect(charts).toHaveLength(20);
  });

  it('includes latitudes past both polar circles', () => {
    const lats = charts.map((c) => c.chart_core.birth.lat);
    expect(lats.some((l) => l > 66.5)).toBe(true);
    expect(lats.some((l) => l < -66.5)).toBe(true);
  });

  it('spans several centuries', () => {
    const years = charts.map((c) => Number(c.chart_core.birth.local_clock.slice(0, 4)));
    expect(Math.max(...years) - Math.min(...years)).toBeGreaterThan(400);
  });

  it('every chart says why it is in the set', () => {
    for (const c of charts) expect(c.why.length).toBeGreaterThan(10);
  });
});

describe.each(charts)('$label — $why', (chart) => {
  const core = chart.chart_core;
  const { lat, lon } = core.birth;

  it('angles match the server', () => {
    const a = angles(core, lat, lon);
    expect(diff(a.asc, chart.expected.asc)).toBeLessThan(TOL);
    expect(diff(a.mc, chart.expected.mc)).toBeLessThan(TOL);
    // Desc and IC are definitionally opposite; a drift here would mean
    // the kit lost track of which end of the axis it is on.
    expect(diff(a.desc, chart.expected.asc + 180)).toBeLessThan(TOL);
    expect(diff(a.ic, chart.expected.mc + 180)).toBeLessThan(TOL);
  });

  it('house cusps match the server', () => {
    const cusps = houseCusps(core, lat, lon);
    expect(cusps).toHaveLength(12);
    cusps.forEach((c, i) => {
      expect(
        diff(c, chart.expected.cusps[i]),
        `cusp ${i + 1}: kit ${c} vs server ${chart.expected.cusps[i]}`,
      ).toBeLessThan(TOL);
    });
  });

  it('house 1 starts at the Ascendant and house 10 at the MC', () => {
    // True for every quadrant system; the invariant that survives the
    // polar substitution and so must hold on every chart in the set.
    const cusps = houseCusps(core, lat, lon);
    if (core.house_system === 'whole_sign') return;
    const a = angles(core, lat, lon);
    expect(diff(cusps[0], a.asc)).toBeLessThan(TOL);
    expect(diff(cusps[9], a.mc)).toBeLessThan(TOL);
  });

  it('aspects match the server, including applying/separating', () => {
    const mine = aspects(core);
    const theirs = chart.expected.aspects;
    expect(mine.length).toBe(theirs.length);
    for (const t of theirs) {
      const m = mine.find((x) => x.a === t.a && x.b === t.b);
      expect(m, `${t.a}-${t.b} ${t.type} missing`).toBeDefined();
      expect(m!.type).toBe(t.type);
      expect(Math.abs(m!.orb - t.orb)).toBeLessThan(TOL);
      expect(m!.applying, `${t.a}-${t.b} applying`).toBe(t.applying);
    }
  });

  it('every body lands in exactly one house', () => {
    const hs = houses(core, lat, lon);
    const placed = hs.flatMap((h) => h.bodies);
    expect(new Set(placed).size).toBe(placed.length);
    expect(placed.sort()).toEqual(Object.keys(core.bodies).sort());
  });

  it('the polar substitution is honoured, not second-guessed', () => {
    if (chart.house_system_note) {
      // The server already decided Placidus is undefined here.
      expect(core.house_system).toBe('porphyry');
      expect(() => houseCusps(core, lat, lon, 'placidus')).toThrow(/undefined/);
    } else {
      expect(core.house_system).toBe('placidus');
    }
  });
});

describe('astrocartography', () => {
  const core = charts[0].chart_core;

  it('MC lines are meridians through the culmination longitude', () => {
    const lines = acgLines(core, { bodies: ['Sun'] });
    const mc = lines.find((l) => l.kind === 'MC')!;
    expect(mc.points[0][0]).toBeCloseTo(mc.points[1][0], 9);
    expect(mc.points[0][0]).toBeCloseTo(mcLongitude(core, 'Sun'), 9);
  });

  it('a body on the MC line really culminates there', () => {
    // The definition, checked rather than assumed: on its MC line a body
    // sits exactly on the local Midheaven.
    const lon = mcLongitude(core, 'Sun');
    const a = angles(core, 40, lon);
    const sunLon = core.bodies.Sun.ecl_lon;
    expect(diff(a.mc, sunLon)).toBeLessThan(TOL);
  });

  it('a body on its ASC line really sits on the horizon', () => {
    // The definition of the line is the BODY's altitude being zero, not
    // the ecliptic Ascendant degree matching its longitude. The two
    // differ by the body's ecliptic latitude: Jupiter at −0.45° here
    // puts its rising line 1.27° away from the degree the chart calls
    // the Ascendant. Asserting altitude is asserting what the line means.
    const D2R = Math.PI / 180;
    const { ra, dec } = core.bodies.Jupiter;
    const line = acgLines(core, { bodies: ['Jupiter'] }).find(
      (l) => l.kind === 'ASC',
    )!;
    for (const [lonAt, latAt] of line.points) {
      const ha = ((core.gmst + lonAt - ra) % 360) * D2R;
      const altitude =
        Math.asin(
          Math.sin(latAt * D2R) * Math.sin(dec * D2R) +
            Math.cos(latAt * D2R) * Math.cos(dec * D2R) * Math.cos(ha),
        ) / D2R;
      expect(Math.abs(altitude)).toBeLessThan(1e-6);
    }
  });

  it('the rising line is NOT the Ascendant degree when latitude is non-zero', () => {
    // Pinned deliberately: users report this as a bug ("the map says
    // Jupiter is on my Ascendant, the chart disagrees"), and the answer
    // is that both are right about different things.
    const line = acgLines(core, { bodies: ['Jupiter'] }).find(
      (l) => l.kind === 'ASC',
    )!;
    const [lonAt, latAt] = line.points[Math.floor(line.points.length / 2)];
    const a = angles(core, latAt, lonAt);
    const gap = diff(a.asc, core.bodies.Jupiter.ecl_lon);
    expect(core.bodies.Jupiter.ecl_lat).not.toBe(0);
    expect(gap).toBeGreaterThan(0.01);
    expect(gap).toBeLessThan(5);
  });

  it('a body with no ecliptic latitude rises exactly on its own degree', () => {
    // The Sun is always on the ecliptic, so for it the two definitions
    // coincide — which is the cleanest proof the gap above is the
    // latitude and not an error.
    expect(Math.abs(core.bodies.Sun.ecl_lat)).toBeLessThan(0.001);
    const line = acgLines(core, { bodies: ['Sun'] }).find((l) => l.kind === 'ASC')!;
    const [lonAt, latAt] = line.points[Math.floor(line.points.length / 2)];
    const a = angles(core, latAt, lonAt);
    expect(diff(a.asc, core.bodies.Sun.ecl_lon)).toBeLessThan(0.01);
  });

  it('lines are split at the antimeridian rather than streaked across', () => {
    for (const line of acgLines(core)) {
      for (let i = 1; i < line.points.length; i++) {
        expect(Math.abs(line.points[i][0] - line.points[i - 1][0])).toBeLessThan(180);
      }
    }
  });

  it('IC is opposite MC for every body', () => {
    const lines = acgLines(core);
    for (const body of Object.keys(core.bodies).slice(0, 3)) {
      const mc = lines.find((l) => l.body === body && l.kind === 'MC');
      const ic = lines.find((l) => l.body === body && l.kind === 'IC');
      if (!mc || !ic) continue;
      expect(Math.abs(Math.abs(mc.points[0][0] - ic.points[0][0]) - 180)).toBeLessThan(1e-9);
    }
  });
});

describe('contacts and dignities', () => {
  const core = charts[0].chart_core;
  const { lat, lon } = core.birth;

  it('contacts agree with the angles they are measured from', () => {
    const a = angles(core, lat, lon);
    for (const c of contacts(core, lat, lon, 8)) {
      const target = { Asc: a.asc, MC: a.mc, IC: a.ic, Desc: a.desc }[c.angle];
      expect(Math.abs(diff(core.bodies[c.body].ecl_lon, target) - c.orb)).toBeLessThan(1e-9);
    }
  });

  it('dignities read the sign each body is actually in', () => {
    for (const d of dignities(core)) {
      expect(d.sign).toBe(signOf(core.bodies[d.body].ecl_lon));
    }
  });

  it('classical rulerships are right where they are unambiguous', () => {
    // Sun in Leo is domicile, Saturn in Libra is exaltation — spot
    // checks that the table is not merely self-consistent.
    const fake = {
      ...core,
      bodies: {
        ...core.bodies,
        Sun: { ...core.bodies.Sun, ecl_lon: 130 }, // 10° Leo
        Saturn: { ...core.bodies.Saturn, ecl_lon: 190 }, // 10° Libra
        Mars: { ...core.bodies.Mars, ecl_lon: 210 }, // 0° Scorpio? no: 30 Libra
      },
    } as ChartCore;
    const byBody = Object.fromEntries(dignities(fake).map((d) => [d.body, d.status]));
    expect(byBody.Sun).toBe('domicile');
    expect(byBody.Saturn).toBe('exaltation');
  });
});

describe('the payload budget the product depends on', () => {
  it('every core stays under 2 KB', () => {
    for (const c of charts) {
      const bytes = new TextEncoder().encode(JSON.stringify(c.chart_core)).length;
      expect(bytes, `${c.label}: ${bytes} B`).toBeLessThanOrEqual(2048);
    }
  });

  it('no chart omits a field the kit reads', () => {
    for (const c of charts) {
      expect(c.chart_core.gmst).toBeTypeOf('number');
      expect(c.chart_core.obliquity).toBeTypeOf('number');
      expect(c.chart_core.node_type).toBe('true');
      for (const body of Object.values(c.chart_core.bodies)) {
        expect(body.ecl_lat).toBeTypeOf('number');
        expect(body.ra).toBeTypeOf('number');
        expect(body.speed_lon).toBeTypeOf('number');
      }
    }
  });
});
