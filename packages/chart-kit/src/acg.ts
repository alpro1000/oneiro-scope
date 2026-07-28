/**
 * Astrocartography loci — the map the prototype proved out.
 *
 * MC/IC lines are meridians: a body culminates at the longitude where
 * local sidereal time equals its right ascension, so the line is
 * vertical and needs no latitude sweep. Asc/Desc lines are horizon
 * curves: the longitude where a body rises depends on latitude through
 * its ascensional difference, so those are sampled.
 *
 * A line marks where the BODY is on the angle — altitude zero for
 * Asc/Desc — computed from its actual right ascension and declination.
 * That is not the same as the ecliptic degree the chart calls the
 * Ascendant: a body with ecliptic latitude rises a little before or
 * after the ecliptic point sharing its longitude (Jupiter at −0.45°
 * separates them by ~1.3°). Both numbers are correct about different
 * things, and users do report the difference as a bug, so the golden
 * tests pin both behaviours explicitly.
 *
 * Reference: Jim Lewis, "Astro*Carto*Graphy" (1976).
 */

import type { ChartCore } from './types';
import { norm360 } from './angles';

const D2R = Math.PI / 180;
const R2D = 180 / Math.PI;

export type LineKind = 'MC' | 'IC' | 'ASC' | 'DESC';

export interface AcgLine {
  body: string;
  kind: LineKind;
  /** [lon, lat] pairs, ready for a polyline. Split on antimeridian. */
  points: [number, number][];
}

/** Longitude where a body culminates (its MC line). */
export function mcLongitude(core: ChartCore, body: string): number {
  const ra = core.bodies[body].ra;
  const lon = norm360(ra - core.gmst);
  return lon > 180 ? lon - 360 : lon;
}

/**
 * Latitude sweep for the horizon curves. Poleward of the point where a
 * body becomes circumpolar it never rises, so the curve simply ends —
 * that gap is real geometry, not missing data.
 */
const DEFAULT_LAT_RANGE: [number, number] = [-85, 85];

function horizonPoints(
  core: ChartCore,
  body: string,
  rising: boolean,
  latRange: [number, number],
  step: number,
): [number, number][] {
  const { ra, dec } = core.bodies[body];
  const pts: [number, number][] = [];
  for (let lat = latRange[0]; lat <= latRange[1]; lat += step) {
    const t = -Math.tan(dec * D2R) * Math.tan(lat * D2R);
    if (Math.abs(t) > 1) continue; // circumpolar here: never rises or sets
    const ha = Math.acos(t) * R2D; // hour angle at rising (negative side)
    const lon = norm360(ra - core.gmst + (rising ? -ha : ha));
    pts.push([lon > 180 ? lon - 360 : lon, lat]);
  }
  return pts;
}

/** Split a polyline where it wraps the antimeridian, so it doesn't streak. */
function splitOnWrap(points: [number, number][]): [number, number][][] {
  const segments: [number, number][][] = [];
  let current: [number, number][] = [];
  for (const p of points) {
    if (current.length && Math.abs(p[0] - current[current.length - 1][0]) > 180) {
      segments.push(current);
      current = [];
    }
    current.push(p);
  }
  if (current.length) segments.push(current);
  return segments;
}

/**
 * Every planetary line for the map.
 *
 * @param bodies Which bodies to draw; defaults to the ten classical ones
 *   (nodes and Chiron make the map unreadable at typical zoom levels).
 */
export function acgLines(
  core: ChartCore,
  options: {
    bodies?: string[];
    latRange?: [number, number];
    step?: number;
  } = {},
): AcgLine[] {
  const {
    bodies = [
      'Sun', 'Moon', 'Mercury', 'Venus', 'Mars',
      'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto',
    ],
    latRange = DEFAULT_LAT_RANGE,
    step = 1,
  } = options;

  const out: AcgLine[] = [];
  for (const body of bodies) {
    if (!(body in core.bodies)) continue;

    const mcLon = mcLongitude(core, body);
    const icLon = mcLon > 0 ? mcLon - 180 : mcLon + 180;
    out.push({
      body, kind: 'MC',
      points: [[mcLon, latRange[0]], [mcLon, latRange[1]]],
    });
    out.push({
      body, kind: 'IC',
      points: [[icLon, latRange[0]], [icLon, latRange[1]]],
    });

    for (const [kind, rising] of [['ASC', true], ['DESC', false]] as const) {
      for (const seg of splitOnWrap(
        horizonPoints(core, body, rising, latRange, step),
      )) {
        if (seg.length > 1) out.push({ body, kind, points: seg });
      }
    }
  }
  return out;
}
