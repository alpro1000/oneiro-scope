/**
 * Natal chart wheel — a simplified, real-data-driven diagram (not a
 * professional rotated chart wheel: the ring is a fixed Aries-at-top
 * zodiac band, and the Ascendant line lands at its SIGN's boundary,
 * not its exact degree, since the API only returns the Ascendant's
 * sign — see NatalChartResponse.ascendant). The planets/aspects
 * TABLES elsewhere on the page remain the precise source; this is a
 * supporting illustration, not a replacement for them.
 */
import type { Aspect, PlanetPosition } from '../lib/astrology-client';

const SIGN_ORDER = [
  'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
  'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces',
];
const SIGN_GLYPH: Record<string, string> = {
  aries: '♈', taurus: '♉', gemini: '♊', cancer: '♋', leo: '♌', virgo: '♍',
  libra: '♎', scorpio: '♏', sagittarius: '♐', capricorn: '♑', aquarius: '♒', pisces: '♓',
};
const PLANET_GLYPH: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂', jupiter: '♃',
  saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
  north_node: '☊', south_node: '☋', chiron: '⚷',
};
// Harmonious aspects read warm (gold), hard aspects read as tension
// (danger/ember), neutral ones stay border-grey — a visual cue, not
// a new interpretive claim (the tables carry the actual reading).
const ASPECT_TONE: Record<string, string> = {
  trine: 'var(--gold)', sextile: 'var(--gold)',
  square: 'var(--danger)', opposition: 'var(--danger)',
  conjunction: 'var(--ink-faint)', quincunx: 'var(--ink-faint)',
};

function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

export interface NatalWheelProps {
  planets: PlanetPosition[];
  aspects: Aspect[];
  ascendantSign?: string;
}

export default function NatalWheel({ planets, aspects, ascendantSign }: NatalWheelProps) {
  const cx = 160;
  const cy = 160;
  const rOuter = 140;
  const rZodiac = 118;
  const rPlanet = 96;
  const rInner = 44;

  const byPlanet = new Map(planets.map((p) => [p.planet?.toLowerCase(), p]));

  return (
    <svg viewBox="0 0 320 320" role="img" aria-label="Natal chart wheel" className="w-full max-w-[340px]">
      <circle cx={cx} cy={cy} r={rOuter} fill="none" stroke="var(--border)" strokeWidth={1.4} />
      <circle cx={cx} cy={cy} r={rPlanet} fill="none" stroke="var(--border)" strokeWidth={1} />
      <circle cx={cx} cy={cy} r={rInner} fill="none" stroke="var(--border)" strokeWidth={1} />

      {/* 12 zodiac sectors + glyphs */}
      {SIGN_ORDER.map((sign, i) => {
        const a = i * 30;
        const [x1, y1] = polar(cx, cy, rInner, a);
        const [x2, y2] = polar(cx, cy, rOuter, a);
        const [gx, gy] = polar(cx, cy, rZodiac, a + 15);
        return (
          <g key={sign}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--border)" strokeWidth={1} />
            <text x={gx} y={gy + 4} textAnchor="middle" fontSize={15} fill="var(--gold-strong)">
              {SIGN_GLYPH[sign]}
            </text>
          </g>
        );
      })}

      {/* Aspect lines between planets, colored by harmonious/hard/neutral */}
      {aspects.map((asp, i) => {
        const p1 = byPlanet.get(asp.planet1?.toLowerCase());
        const p2 = byPlanet.get(asp.planet2?.toLowerCase());
        if (!p1 || !p2) return null;
        const [x1, y1] = polar(cx, cy, rPlanet, p1.degree);
        const [x2, y2] = polar(cx, cy, rPlanet, p2.degree);
        return (
          <line
            key={i}
            x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={ASPECT_TONE[asp.aspect_type?.toLowerCase()] || 'var(--ink-faint)'}
            strokeWidth={1}
            strokeDasharray={asp.aspect_type === 'conjunction' ? undefined : '2 3'}
            opacity={0.75}
          />
        );
      })}

      {/* Ascendant — sign-boundary precision only (see file header) */}
      {ascendantSign && SIGN_ORDER.includes(ascendantSign.toLowerCase()) && (
        <>
          {(() => {
            const a = SIGN_ORDER.indexOf(ascendantSign.toLowerCase()) * 30;
            const [ox, oy] = polar(cx, cy, rOuter, a);
            const [lx, ly] = polar(cx, cy, rOuter + 14, a);
            return (
              <>
                <line x1={cx} y1={cy} x2={ox} y2={oy} stroke="var(--gold-strong)" strokeWidth={2} />
                <text x={lx} y={ly + 3} textAnchor="middle" fontSize={9} fill="var(--gold-strong)" fontFamily="var(--font-mono)">
                  ASC
                </text>
              </>
            );
          })()}
        </>
      )}

      {/* Planets at their real absolute degree */}
      {planets.map((p) => {
        const [x, y] = polar(cx, cy, rPlanet, p.degree);
        const glyph = PLANET_GLYPH[p.planet?.toLowerCase()] || '●';
        return (
          <g key={p.planet}>
            <circle cx={x} cy={y} r={9} fill="var(--surface-strong)" stroke="var(--gold)" strokeWidth={1.2} />
            <text x={x} y={y + 4} textAnchor="middle" fontSize={11} fill="var(--gold-strong)">
              {glyph}
            </text>
            {p.retrograde && (
              <text x={x + 11} y={y - 7} fontSize={8} fill="var(--danger)">℞</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
