/**
 * Aspects, angle contacts and dignities — all pure lookups over the core.
 *
 * The applying/separating rule here mirrors the server's (WP-3): it
 * comes from both bodies' real speeds, never from a "which planet is
 * usually faster" heuristic. A retrograde body flips the geometry by
 * itself.
 */

import type { Angles, Aspect, AngleContact, ChartCore, Dignity } from './types';
import { angles, norm360, sep180 } from './angles';

/** Exact angle and default maximum orb, matching the server's policy. */
export const ASPECTS: Record<string, { angle: number; orb: number }> = {
  conjunction: { angle: 0, orb: 10 },
  opposition: { angle: 180, orb: 10 },
  trine: { angle: 120, orb: 8 },
  square: { angle: 90, orb: 8 },
  sextile: { angle: 60, orb: 6 },
  quincunx: { angle: 150, orb: 3 },
};

/** Bodies the server also aspects — nodes and Chiron are excluded. */
const ASPECTING = [
  'Sun', 'Moon', 'Mercury', 'Venus', 'Mars',
  'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto',
];

export function aspects(
  core: ChartCore,
  orbPolicy: Record<string, number> = {},
): Aspect[] {
  const out: Aspect[] = [];
  const names = ASPECTING.filter((n) => n in core.bodies);

  for (let i = 0; i < names.length; i++) {
    for (let j = i + 1; j < names.length; j++) {
      const a = core.bodies[names[i]];
      const b = core.bodies[names[j]];
      // Signed separation drives the sign of d|s|/dt below; |s| is the
      // angular distance the aspect is measured from.
      const s = sep180(a.ecl_lon, b.ecl_lon);
      const delta = Math.abs(s);
      const speedDiff = a.speed_lon - b.speed_lon;
      const dDelta = s >= 0 ? speedDiff : -speedDiff;

      for (const [type, spec] of Object.entries(ASPECTS)) {
        const maxOrb = orbPolicy[type] ?? spec.orb;
        const deviation = delta - spec.angle;
        if (Math.abs(deviation) <= maxOrb) {
          out.push({
            a: names[i],
            b: names[j],
            type,
            orb: Math.abs(deviation),
            // |deviation| shrinking ⇔ the aspect is closing on exact.
            applying: deviation * dDelta < 0,
            speedDiff,
          });
          break;
        }
      }
    }
  }
  return out;
}

/** Bodies sitting on one of the four angles at a location. */
export function contacts(
  core: ChartCore,
  lat: number,
  lon: number,
  orb = 8,
): AngleContact[] {
  const ang: Angles = angles(core, lat, lon);
  const targets: [AngleContact['angle'], number][] = [
    ['Asc', ang.asc], ['MC', ang.mc], ['IC', ang.ic], ['Desc', ang.desc],
  ];
  const out: AngleContact[] = [];
  for (const [name, body] of Object.entries(core.bodies)) {
    for (const [angleName, angleLon] of targets) {
      const d = Math.abs(sep180(body.ecl_lon, angleLon));
      if (d <= orb) out.push({ body: name, angle: angleName, orb: d });
    }
  }
  return out.sort((x, y) => x.orb - y.orb);
}

export const SIGNS = [
  'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
  'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces',
];

export const signOf = (longitude: number): string =>
  SIGNS[Math.floor(norm360(longitude) / 30) % 12];

export const degreeInSign = (longitude: number): number => norm360(longitude) % 30;

// Classical rulerships. Traditional only — the modern Uranus/Neptune/
// Pluto assignments are a separate tradition and mixing the two silently
// would be exactly the kind of unlabelled blend the project forbids.
const DOMICILE: Record<string, string[]> = {
  Sun: ['leo'],
  Moon: ['cancer'],
  Mercury: ['gemini', 'virgo'],
  Venus: ['taurus', 'libra'],
  Mars: ['aries', 'scorpio'],
  Jupiter: ['sagittarius', 'pisces'],
  Saturn: ['capricorn', 'aquarius'],
};
const EXALTATION: Record<string, string> = {
  Sun: 'aries', Moon: 'taurus', Mercury: 'virgo', Venus: 'pisces',
  Mars: 'capricorn', Jupiter: 'cancer', Saturn: 'libra',
};
const opposite = (sign: string): string =>
  SIGNS[(SIGNS.indexOf(sign) + 6) % 12];

/** Essential dignity of each classical body, by sign. */
export function dignities(core: ChartCore): Dignity[] {
  const out: Dignity[] = [];
  for (const body of Object.keys(DOMICILE)) {
    if (!(body in core.bodies)) continue;
    const sign = signOf(core.bodies[body].ecl_lon);
    let status = 'peregrine';
    if (DOMICILE[body].includes(sign)) status = 'domicile';
    else if (EXALTATION[body] === sign) status = 'exaltation';
    else if (DOMICILE[body].some((s) => opposite(s) === sign)) status = 'detriment';
    else if (EXALTATION[body] && opposite(EXALTATION[body]) === sign) status = 'fall';
    out.push({ body, sign, status });
  }
  return out;
}
