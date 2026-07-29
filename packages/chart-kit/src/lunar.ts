/**
 * The lunar day of the chart's own moment, from the core alone.
 *
 * This is not an approximation of the server's answer — it is the same
 * arithmetic. `backend/services/lunar/engine.py` derives the lunar day
 * purely from the elongation of the Moon from the Sun:
 *
 *     phase_angle  = (moon_lon - sun_lon) mod 360
 *     moon_age_days = phase_angle / 360 * SYNODIC_MONTH
 *     lunar_day    = clamp(floor(moon_age_days) + 1, 1, 30)
 *
 * Both longitudes ride in `chart_core.bodies`, so the whole thing is
 * free and offline, and the golden tests check it against the server on
 * all 20 charts.
 *
 * ILLUMINATION IS DELIBERATELY ABSENT. The server takes it from
 * `swe.pheno_ut`, which accounts for the Moon's actual phase geometry.
 * WP-16 replaced the flat `(1 - cos)/2` formula precisely because it was
 * wrong by up to ~4 percentage points (74.08% vs 77.85% on 2026-08-03),
 * and that formula is the only one derivable from a longitude pair.
 * Re-deriving it here would reintroduce a known error under a name that
 * looks authoritative — so illumination stays a server number.
 *
 * SCOPE. A `chart_core` describes ONE instant, so this answers "which
 * lunar day was this chart born on". A lunar calendar over other dates
 * needs the Sun and Moon at those dates, which this payload does not
 * contain: that is a network call, and §6 requires saying so rather than
 * quietly showing something.
 */

import type { ChartCore } from './types';
import { norm360 } from './angles';
import { signOf } from './aspects';

/** Mean synodic month in days — the server's constant, to the digit. */
export const SYNODIC_MONTH = 29.53058867;

export type MoonPhase =
  | 'new_moon'
  | 'waxing_crescent'
  | 'first_quarter'
  | 'waxing_gibbous'
  | 'full_moon'
  | 'waning_gibbous'
  | 'last_quarter'
  | 'waning_crescent';

export interface LunarMoment {
  /** Moon − Sun, degrees 0–360. */
  phaseAngle: number;
  /** Days since the mean new moon. */
  moonAgeDays: number;
  /** 1–30, the traditional lunar day. */
  lunarDay: number;
  phase: MoonPhase;
  /**
   * Sign the Moon occupies, lowercase — the kit's own vocabulary, the
   * same one `signOf` and `dignities` speak. The server capitalises
   * ("Aries"); one vocabulary inside the kit is worth more than matching
   * the server's casing, so the golden test compares case-insensitively.
   */
  moonSign: string;
  /**
   * Always false — a reminder at the type level that this object carries
   * no illuminated fraction and that a client must ask the server for
   * one rather than computing it. See the module docstring.
   */
  illuminationKnown: false;
}

/** The server's eight-way split of the phase angle, boundaries included. */
export function phaseOf(angleDeg: number): MoonPhase {
  const a = norm360(angleDeg);
  if (a < 22.5 || a >= 337.5) return 'new_moon';
  if (a < 67.5) return 'waxing_crescent';
  if (a < 112.5) return 'first_quarter';
  if (a < 157.5) return 'waxing_gibbous';
  if (a < 202.5) return 'full_moon';
  if (a < 247.5) return 'waning_gibbous';
  if (a < 292.5) return 'last_quarter';
  return 'waning_crescent';
}

/** Lunar state at the chart's own instant. */
export function lunarDay(core: ChartCore): LunarMoment {
  const sun = core.bodies.Sun;
  const moon = core.bodies.Moon;
  if (!sun || !moon) {
    // Not a silent zero: a core without both luminaries is a broken
    // payload, and answering "lunar day 1" would be indistinguishable
    // from a real new moon (conventions.md §12).
    throw new Error(
      'chart_core is missing Sun or Moon — the lunar day is the elongation ' +
        'between them and cannot be derived without both',
    );
  }
  const phaseAngle = norm360(moon.ecl_lon - sun.ecl_lon);
  const moonAgeDays = (phaseAngle / 360) * SYNODIC_MONTH;
  return {
    phaseAngle,
    moonAgeDays,
    lunarDay: Math.max(1, Math.min(30, Math.floor(moonAgeDays) + 1)),
    phase: phaseOf(phaseAngle),
    moonSign: signOf(moon.ecl_lon),
    illuminationKnown: false,
  };
}
