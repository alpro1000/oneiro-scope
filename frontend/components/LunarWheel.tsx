/**
 * Lunar phase wheel — 8 canonical phases positioned around a ring
 * (order matches backend/services/lunar/engine.py::_phase_key), the
 * current phase highlighted from the real `phase_key`/`illumination`
 * the lunar service returns. Purely illustrative; the text summary
 * next to it carries the actual reading.
 */
const PHASE_ORDER = [
  'new_moon', 'waxing_crescent', 'first_quarter', 'waxing_gibbous',
  'full_moon', 'waning_gibbous', 'last_quarter', 'waning_crescent',
];
const PHASE_ICON: Record<string, string> = {
  new_moon: '🌑', waxing_crescent: '🌒', first_quarter: '🌓', waxing_gibbous: '🌔',
  full_moon: '🌕', waning_gibbous: '🌖', last_quarter: '🌗', waning_crescent: '🌘',
};

function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

export interface LunarWheelProps {
  phaseKey?: string;
  illumination?: number; // 0..1
}

export default function LunarWheel({ phaseKey, illumination }: LunarWheelProps) {
  const cx = 160;
  const cy = 160;
  const r = 118;
  const currentIndex = phaseKey ? PHASE_ORDER.indexOf(phaseKey) : -1;

  return (
    <svg viewBox="0 0 320 320" role="img" aria-label="Lunar phase wheel" className="w-full max-w-[340px]">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--border)" strokeWidth={1.2} />
      <circle cx={cx} cy={cy} r={r - 28} fill="none" stroke="var(--border)" strokeWidth={1} />

      {PHASE_ORDER.map((key, i) => {
        const isCurrent = i === currentIndex;
        const [x, y] = polar(cx, cy, r - 24, i * 45);
        return (
          <g key={key}>
            {isCurrent && (
              <circle cx={x} cy={y} r={22} fill="var(--surface-strong)" stroke="var(--gold-strong)" strokeWidth={1.6} />
            )}
            <text x={x} y={y + 8} textAnchor="middle" fontSize={isCurrent ? 22 : 17}>
              {PHASE_ICON[key]}
            </text>
          </g>
        );
      })}

      {typeof illumination === 'number' && (
        <text x={cx} y={cy + 5} textAnchor="middle" fontSize={11} fill="var(--ink-muted)" fontFamily="var(--font-mono)">
          {Math.round(illumination * 100)}%
        </text>
      )}
    </svg>
  );
}
