/**
 * Tying a coded clause back to the span of dream text it came from.
 *
 * A pure module rather than part of the view, for two reasons: it is the one
 * piece of real logic in `dream-evidence.ts` and deserves tests, and a view
 * file calls `mountView` at import time, so it cannot be imported outside a
 * browser at all.
 */

import { esc } from './view';

export interface Evidence {
  category?: string;
  subtype?: string;
  actor?: string;
  target?: string | null;
  evidence?: string;
  source?: string;
  confidence?: number;
}

/**
 * The dream text with each evidence clause wrapped in a mark.
 *
 * Matching is by substring, case- and ё-insensitively. The coder lowercases
 * and folds ё→е while segmenting, so a clause it reports as «за мной гналась
 * собака» appears in the text as «За мной гналась собака» — a case-sensitive
 * search drops it, and dropping one silently is precisely what this view
 * exists to prevent. Folding is applied only to FIND the span; the slice
 * rendered is taken from the original text, so the user reads their own words.
 *
 * The fold is length-preserving (`toLowerCase` on Cyrillic and Latin, plus a
 * one-for-one ё→е), which keeps indices in the folded string valid in the
 * original. Anything that still fails to match is a genuine mismatch and is
 * left unmarked rather than approximated: a fuzzy match would highlight the
 * wrong phrase and misattribute the evidence.
 */
const fold = (s: string) => s.toLowerCase().replace(/ё/g, 'е');

export function markUp(text: string, evidence: Evidence[]): string {
  const haystack = fold(text);
  const clauses = evidence
    .map((e, i) => ({ clause: fold((e.evidence ?? '').trim()), i }))
    .filter((c) => c.clause.length > 2);

  type Span = { start: number; end: number; i: number };
  const spans: Span[] = [];
  for (const { clause, i } of clauses) {
    let from = 0;
    while (from <= haystack.length) {
      const at = haystack.indexOf(clause, from);
      if (at === -1) break;
      const overlaps = spans.some((s) => at < s.end && at + clause.length > s.start);
      if (!overlaps) {
        spans.push({ start: at, end: at + clause.length, i });
        break;
      }
      from = at + 1;
    }
  }
  spans.sort((a, b) => a.start - b.start);

  let out = '';
  let cursor = 0;
  for (const s of spans) {
    out += esc(text.slice(cursor, s.start));
    out += `<mark class="ev" data-i="${s.i}">${esc(text.slice(s.start, s.end))}`
      + `<sup>${s.i + 1}</sup></mark>`;
    cursor = s.end;
  }
  out += esc(text.slice(cursor));
  return out;
}
