import type { ReactNode } from 'react';

/**
 * Frame for a legal document (privacy / terms / disclaimer).
 *
 * Replaces `LegalSkeleton`, which held a "text is being prepared" placeholder.
 * The bodies are now written, and written from an audit of what the code
 * actually does rather than from the usual boilerplate — see the note each
 * page carries about review.
 *
 * Bilingual on one page, not two routes: these URLs are referenced from
 * connector directories and from other people's dashboards, so they must
 * resolve for everyone without a locale prefix or a redirect.
 */

export interface LegalSection {
  h: string;
  /** Paragraphs. */
  p?: string[];
  /** Bulleted points, rendered after the paragraphs. */
  list?: string[];
  /** Label/value rows — used for "what is stored where" tables. */
  rows?: [string, string][];
}

export default function LegalDoc({
  eyebrow,
  titleRu,
  titleEn,
  updated,
  lede,
  sections,
  children,
}: {
  eyebrow: string;
  titleRu: string;
  titleEn: string;
  /** ISO date, shown in mono — a legal document without one is unusable. */
  updated: string;
  lede?: string;
  sections: LegalSection[];
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
      <p style={{
        fontFamily: 'var(--font-display)', fontStyle: 'italic', color: 'var(--muted)',
        fontSize: 'clamp(17px,3vw,22px)', margin: '4px 0 0',
      }}>
        {titleEn}
      </p>

      {lede && <p className="legal-lede">{lede}</p>}

      <div className="legal-review">
        <p style={{ margin: 0 }}>
          Этот текст описывает то, что система делает на самом деле — он написан
          по аудиту кода, а не по шаблону. Юридическую проверку он ещё не проходил:
          до публичного запуска его должен посмотреть юрист.
        </p>
        <p style={{ margin: '7px 0 0', color: 'var(--dim)' }}>
          This text describes what the system actually does — it was written from
          a code audit, not from a template. It has not yet been reviewed by a
          lawyer, and should be before public launch.
        </p>
      </div>

      {sections.map((s) => (
        <section key={s.h} className="legal-section">
          <h2>{s.h}</h2>
          {s.p?.map((para) => <p key={para}>{para}</p>)}
          {s.list && <ul>{s.list.map((i) => <li key={i}>{i}</li>)}</ul>}
          {s.rows && (
            <dl className="legal-rows">
              {s.rows.map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      ))}

      {children}

      <p className="num legal-updated">
        Последнее обновление · last updated: {updated}
      </p>
    </article>
  );
}
