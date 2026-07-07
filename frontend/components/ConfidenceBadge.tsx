/**
 * Shared confidence-ladder indicator (docs/design/product-design-brief.md
 * §3): the same pill everywhere on the site, only the number and source
 * caption change per section (1.0 ephemeris, 0.8 symbol dictionary,
 * 0.6 physiognomy tradition, etc.).
 */
export default function ConfidenceBadge({
  score,
  source,
  label = 'Достоверность',
}: {
  score: number;
  source: string;
  label?: string;
}) {
  const fillPct = Math.max(0, Math.min(1, score)) * 100;

  return (
    <div className="inline-flex max-w-full flex-wrap items-center gap-2.5 rounded-full border border-border bg-surfaceStrong px-3 py-2">
      <span className="font-mono text-[0.62rem] uppercase tracking-widest text-inkFaint">
        {label}
      </span>
      <span className="h-[5px] w-11 shrink-0 overflow-hidden rounded-full bg-border">
        <span
          className="block h-full rounded-full bg-gold"
          style={{width: `${fillPct}%`}}
        />
      </span>
      <span className="font-mono text-sm font-semibold text-goldStrong">
        {score.toFixed(2)}
      </span>
      <span className="font-mono text-xs text-inkFaint">{source}</span>
    </div>
  );
}
