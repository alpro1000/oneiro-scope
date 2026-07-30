/**
 * Angles and house cusps — the geometry that makes the thin core work.
 *
 * Everything here is a pure function of `chart_core` plus a location:
 * no network, no state, no ephemeris. That is the whole architectural
 * bet, and `golden.test.ts` checks it against the server on 20 charts
 * to 0.01°.
 */

import type { Angles, ChartCore, House, HouseSystem } from './types';

const D2R = Math.PI / 180;
const R2D = 180 / Math.PI;

export const norm360 = (x: number): number => ((x % 360) + 360) % 360;

/** Shortest signed separation between two longitudes, in (−180, 180]. */
export const sep180 = (a: number, b: number): number => {
  const d = norm360(a - b);
  return d > 180 ? d - 360 : d;
};

/** Right ascension of the meridian: sidereal time at the location. */
export const ramc = (core: ChartCore, lon: number): number =>
  norm360(core.gmst + lon);

/**
 * The four angles for any point on Earth.
 *
 * The quadrant correction on the Ascendant is load-bearing, not
 * cosmetic: the arctangent's principal value returns the DESCENDANT for
 * 7.9% of the globe (a 1068-point sweep against Swiss Ephemeris found
 * 84 flips of exactly 180°, all poleward of ~66°). The Ascendant is the
 * eastern horizon point, which always leads the Midheaven by 0–180° in
 * zodiacal order — that is what the correction restores.
 */
export function angles(core: ChartCore, lat: number, lon: number): Angles {
  const r = ramc(core, lon) * D2R;
  const e = core.obliquity * D2R;
  const phi = lat * D2R;

  const mc = norm360(Math.atan2(Math.sin(r), Math.cos(r) * Math.cos(e)) * R2D);
  let asc = norm360(
    Math.atan2(
      Math.cos(r),
      -(Math.sin(r) * Math.cos(e) + Math.tan(phi) * Math.sin(e)),
    ) * R2D,
  );
  if (norm360(asc - mc) > 180) asc = norm360(asc + 180);

  return { asc, mc, desc: norm360(asc + 180), ic: norm360(mc + 180) };
}

/** Ecliptic longitude of the point at a given right ascension. */
const lonAtRa = (raDeg: number, eps: number): number =>
  Math.atan2(Math.sin(raDeg * D2R), Math.cos(raDeg * D2R) * Math.cos(eps));

/**
 * One intermediate Placidus cusp, by iteration on the ascensional
 * difference.
 *
 * Placidus places a cusp where a point has traversed a fixed fraction
 * of its own semi-arc since culminating, so the cusp's position depends
 * on its own declination — hence the fixed-point iteration. Returns
 * null when the point is circumpolar (|tan δ · tan φ| > 1): there is no
 * semi-arc to divide, which is exactly why Placidus is undefined beyond
 * the polar circle.
 */
function placidusCusp(
  ramcDeg: number,
  eps: number,
  phi: number,
  base: number,
  fraction: number,
): number | null {
  let ad = 0;
  for (let i = 0; i < 50; i++) {
    const lam = lonAtRa(ramcDeg + base + fraction * ad, eps);
    const dec = Math.asin(Math.sin(eps) * Math.sin(lam));
    const t = Math.tan(dec) * Math.tan(phi);
    if (Math.abs(t) > 1) return null;
    const next = Math.asin(t) * R2D;
    if (Math.abs(next - ad) < 1e-10) {
      ad = next;
      break;
    }
    ad = next;
  }
  return norm360(lonAtRa(ramcDeg + base + fraction * ad, eps) * R2D);
}

/** Which house a longitude falls in, given the 12 cusps. */
export function houseOf(longitude: number, cusps: number[]): number {
  for (let i = 0; i < 12; i++) {
    const start = cusps[i];
    const end = cusps[(i + 1) % 12];
    const inside =
      end < start
        ? longitude >= start || longitude < end
        : longitude >= start && longitude < end;
    if (inside) return i + 1;
  }
  return 12;
}

/**
 * The latitude past which Placidus and Koch stop existing, for this
 * chart's epoch.
 *
 * Not a hardcoded 66.5°: the polar circle is 90° − obliquity, and the
 * obliquity drifts by ~47″/century, which is why `chart_core` ships it.
 * A binary search against `swe.houses_ex` puts the server's own refusal
 * at exactly this value (66.557962° for a 1990 chart, obliquity
 * 23.442038°), and it refuses for the whole latitude rather than
 * per-cusp — so this is the rule the kit must use to stay in step. A
 * finer per-cusp test would find some polar charts "defined" that the
 * server would have substituted, which is precisely the silent
 * divergence the golden set exists to catch.
 */
const placidusLimit = (core: ChartCore): number => 90 - core.obliquity;

/**
 * Which house system is usable at a given latitude, and why.
 *
 * Relocation is the whole point of the map, and the system that works
 * at the birth place says nothing about the system that works at the
 * target: Placidus is undefined poleward of the polar circle wherever
 * you were born. Resolving per target is what keeps "move a London
 * chart to Tromsø" from throwing and "move a Tromsø chart to London"
 * from silently staying on Porphyry.
 *
 * `_lon` is accepted and ignored: the boundary is a function of
 * latitude alone. It stays in the signature so callers can pass a
 * location as one pair, the way every other function here takes it.
 */
export function resolveSystemFor(
  core: ChartCore,
  lat: number,
  _lon?: number,
): { system: HouseSystem; substituted: boolean } {
  const requested = core.requested_house_system ?? core.house_system;
  if (requested !== 'placidus' && requested !== 'koch') {
    return { system: requested, substituted: false };
  }
  return Math.abs(lat) >= placidusLimit(core)
    ? { system: 'porphyry', substituted: true }
    : { system: requested, substituted: false };
}

/**
 * The twelve house cusps, as absolute ecliptic longitudes.
 *
 * With no explicit `system`, the one usable AT THIS LOCATION is
 * resolved — not the one the payload happened to need at the birth
 * place. Passing a system explicitly forces it, and forcing Placidus
 * where it is undefined throws rather than quietly returning something
 * else.
 */
export function houseCusps(
  core: ChartCore,
  lat: number,
  lon: number,
  system: HouseSystem = resolveSystemFor(core, lat, lon).system,
): number[] {
  const { asc, mc, desc, ic } = angles(core, lat, lon);
  const eps = core.obliquity * D2R;
  const phi = lat * D2R;
  const r = ramc(core, lon);

  if (system === 'whole_sign') {
    const start = Math.floor(asc / 30) * 30;
    return Array.from({ length: 12 }, (_, i) => norm360(start + i * 30));
  }
  if (system === 'equal') {
    return Array.from({ length: 12 }, (_, i) => norm360(asc + i * 30));
  }
  if (system === 'porphyry') {
    // Each quadrant trisected evenly. Defined at every latitude, which
    // is why the server substitutes it beyond the polar circle.
    const q1 = norm360(ic - asc) / 3;
    const q2 = norm360(desc - ic) / 3;
    return [
      asc, norm360(asc + q1), norm360(asc + 2 * q1),
      ic, norm360(ic + q2), norm360(ic + 2 * q2),
      desc, norm360(desc + q1), norm360(desc + 2 * q1),
      mc, norm360(mc + q2), norm360(mc + 2 * q2),
    ].map(norm360);
  }
  if (system === 'placidus') {
    const c11 = placidusCusp(r, eps, phi, 30, 1 / 3);
    const c12 = placidusCusp(r, eps, phi, 60, 2 / 3);
    const c2 = placidusCusp(r, eps, phi, 120, 2 / 3);
    const c3 = placidusCusp(r, eps, phi, 150, 1 / 3);
    // The latitude test comes first and is the authoritative one: for a
    // few sidereal times past the polar circle all four cusps still
    // converge, and returning them would hand back a Placidus chart the
    // server refuses to produce.
    if (
      Math.abs(lat) >= placidusLimit(core) ||
      c11 === null || c12 === null || c2 === null || c3 === null
    ) {
      throw new Error(
        `Placidus is undefined at latitude ${lat}: beyond the polar circle ` +
          `(±${placidusLimit(core).toFixed(4)}° at this epoch) no ecliptic ` +
          `point crosses the horizon, so there is no semi-arc to divide. ` +
          `Omit the system argument to get the one usable here.`,
      );
    }
    return [
      asc, c2, c3, ic,
      norm360(c11 + 180), norm360(c12 + 180),
      desc, norm360(c2 + 180), norm360(c3 + 180),
      mc, c11, c12,
    ];
  }
  throw new Error(`chart-kit does not implement the ${system} house system`);
}

/** Cusps plus the bodies that fall in each house. */
export function houses(
  core: ChartCore,
  lat: number,
  lon: number,
  system: HouseSystem = resolveSystemFor(core, lat, lon).system,
): House[] {
  const cusps = houseCusps(core, lat, lon, system);
  const out: House[] = cusps.map((cusp, i) => ({
    number: i + 1,
    cusp,
    bodies: [],
  }));
  for (const [name, body] of Object.entries(core.bodies)) {
    out[houseOf(body.ecl_lon, cusps) - 1].bodies.push(name);
  }
  return out;
}
