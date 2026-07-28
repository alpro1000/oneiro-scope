/**
 * The `chart_core` contract, as the client sees it.
 *
 * Mirrors `backend/services/astrology/chart_core.py`. The server is the
 * only producer; this package is the only consumer that matters, and
 * the golden tests keep the two in agreement to 0.01°.
 */

/** One body's state at the natal moment. */
export interface BodyState {
  /** Ecliptic longitude, degrees 0–360. */
  ecl_lon: number;
  /** Ecliptic latitude, degrees. Needed to re-derive RA/Dec. */
  ecl_lat: number;
  /** Right ascension, degrees — astrocartography loci live here. */
  ra: number;
  /** Declination, degrees. */
  dec: number;
  /** Longitude speed, degrees/day. Negative means retrograde. */
  speed_lon: number;
  retrograde: boolean;
}

export interface BirthInfo {
  lat: number;
  lon: number;
  /** IANA zone actually applied. */
  tz_used: string;
  /** Pre-formatted ±HH:MM — the value users argue about. */
  utc_offset_used: string;
  tz_source: string;
  local_clock: string;
  utc: string;
  place_label: string;
  /**
   * False when no birth time was supplied. Angles and houses are then
   * meaningless and a client MUST NOT draw them — noon was assumed only
   * so the slow bodies have a position.
   */
  time_known: boolean;
}

export type HouseSystem =
  | 'placidus'
  | 'koch'
  | 'porphyry'
  | 'regiomontanus'
  | 'campanus'
  | 'equal'
  | 'whole_sign';

export interface ChartCore {
  version: string;
  jd_ut: number;
  /**
   * Apparent sidereal time at Greenwich, degrees. Paired with
   * `obliquity` (true): mixing an apparent angle with a mean obliquity
   * shifts the Midheaven by up to ~17″, so the two always travel and
   * are used together.
   */
  gmst: number;
  /** True obliquity of the ecliptic, degrees. */
  obliquity: number;
  birth: BirthInfo;
  bodies: Record<string, BodyState>;
  /** 'true' | 'mean' — which lunar node the payload carries. */
  node_type: string;
  /** The system that is actually defined at this latitude. */
  house_system: HouseSystem;
}

export interface Angles {
  asc: number;
  mc: number;
  desc: number;
  ic: number;
}

export interface House {
  number: number;
  /** Absolute ecliptic longitude of the cusp, degrees. */
  cusp: number;
  /** Bodies falling inside this house. */
  bodies: string[];
}

export interface Aspect {
  a: string;
  b: string;
  type: string;
  /** Deviation from exact, degrees. */
  orb: number;
  /** True while the aspect is closing on exact. */
  applying: boolean;
  /** speed(a) − speed(b), degrees/day. */
  speedDiff: number;
}

export interface AngleContact {
  body: string;
  angle: 'Asc' | 'MC' | 'IC' | 'Desc';
  orb: number;
}

export interface Dignity {
  body: string;
  sign: string;
  /** domicile | exaltation | detriment | fall | peregrine */
  status: string;
}
