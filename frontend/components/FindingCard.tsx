/**
 * Shared "finding card" (docs/design/product-design-brief.md §3, §8,
 * §9): the ONE component for dream symbols, event-forecast factors,
 * and face-reading traits — never three divergent designs. Four
 * visually distinct zones: measurement (mono) -> tradition quote
 * (serif italic, cited) -> plain-language explanation -> plus/minus.
 */
export interface FindingCardProps {
  title: string;
  seenLabel?: string;
  seenText: string;
  traditionQuote: string;
  traditionSource: string;
  humanText: string;
  plusLabel?: string;
  plusText: string;
  minusLabel?: string;
  minusText: string;
  /** Subject-verified observation overriding the dictionary clause —
   * lived reality outranks the 0.6 tradition tier (life-context). */
  lifeContext?: string;
}

export default function FindingCard({
  title,
  seenLabel = 'Система увидела',
  seenText,
  traditionQuote,
  traditionSource,
  humanText,
  plusLabel = 'Что усиливает',
  plusText,
  minusLabel = 'На что обратить внимание',
  minusText,
  lifeContext,
}: FindingCardProps) {
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border bg-surfaceStrong p-5 shadow-gold">
      <h4 className="font-display text-base font-semibold text-ink">{title}</h4>

      <p className="m-0 rounded-md border border-border bg-bgDeep px-3 py-2 font-mono text-xs leading-relaxed text-inkMuted">
        <span className="mb-1 block text-[0.62rem] uppercase tracking-widest text-inkFaint">
          {seenLabel}
        </span>
        {seenText}
      </p>

      <blockquote className="m-0 flex flex-col gap-1.5 border-l-2 border-gold pl-3.5 font-display text-sm italic leading-relaxed text-ink">
        {traditionQuote}
        <cite className="font-mono text-[0.68rem] not-italic text-inkFaint">
          {traditionSource}
        </cite>
      </blockquote>

      <p className="m-0 text-sm leading-relaxed text-inkMuted">{humanText}</p>

      {lifeContext && (
        <p className="m-0 rounded-md border border-gold bg-goldSoft px-3 py-2 text-sm leading-relaxed text-ink">
          ✅ {lifeContext}
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 border-t border-border pt-3 text-sm sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[0.62rem] uppercase tracking-widest text-goldStrong">
            {plusLabel}
          </span>
          <span className="text-inkMuted">{plusText}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[0.62rem] uppercase tracking-widest text-danger">
            {minusLabel}
          </span>
          <span className="text-inkMuted">{minusText}</span>
        </div>
      </div>
    </article>
  );
}
