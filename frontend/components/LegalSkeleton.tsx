import type { ReactNode } from 'react';

/**
 * Empty-but-styled frame for a legal document (privacy / terms / disclaimer).
 *
 * Deliberately a skeleton: the heading and the instrument styling are here so
 * the URL is live and linkable now (the privacy policy is a catalog
 * prerequisite), while the body is a placeholder until the owner supplies the
 * real text. No claims are made in the meantime — the note says plainly that
 * the document is in preparation, rather than implying coverage that does not
 * exist yet.
 */
export default function LegalSkeleton({
  eyebrow,
  titleRu,
  titleEn,
  children,
}: {
  eyebrow: string;
  titleRu: string;
  titleEn: string;
  children?: ReactNode;
}) {
  return (
    <article>
      <span className="eyebrow" style={{ display: 'block', marginBottom: 10 }}>{eyebrow}</span>
      <h1 style={{
        fontFamily: 'var(--font-display)', fontWeight: 400, letterSpacing: '-.015em',
        lineHeight: 1.02, fontSize: 'clamp(30px,6vw,52px)', margin: 0,
      }}>
        {titleRu}
      </h1>
      <p style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', color: 'var(--muted)', fontSize: 'clamp(17px,3vw,22px)', margin: '4px 0 0' }}>
        {titleEn}
      </p>

      <div style={{
        marginTop: 'clamp(22px,4vw,36px)', border: '1px solid var(--grat-2)', background: 'var(--panel)',
        padding: '16px 18px', color: 'var(--muted)', fontSize: 14, lineHeight: 1.6,
      }}>
        <p style={{ margin: 0 }}>
          Черновик. Текст готовится и будет опубликован на этой странице.
        </p>
        <p style={{ margin: '6px 0 0', color: 'var(--dim)' }}>
          Draft. The text is being prepared and will be published on this page.
        </p>
      </div>

      {children}

      <p className="num" style={{ marginTop: 'clamp(22px,4vw,36px)', color: 'var(--dim)', fontSize: 11, letterSpacing: '.05em' }}>
        Последнее обновление · last updated: —
      </p>
    </article>
  );
}
