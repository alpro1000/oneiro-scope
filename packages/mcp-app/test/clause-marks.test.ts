/**
 * The dream view's one non-obvious piece: tying a coded clause back to the
 * span of text it came from. Every count in that view is only worth its
 * evidence, so a clause that fails to highlight is a count with nothing under
 * it — silently.
 */
import { describe, expect, it } from 'vitest';
import { markUp, type Evidence } from '../src/clause-marks';

const ev = (evidence: string): Evidence => ({ category: 'aggression', evidence });

describe('markUp', () => {
  it('marks a clause the coder reported in lower case', () => {
    // The regression that shipped: the coder lowercases while segmenting, so
    // it reports «за мной гналась собака» for a sentence that starts «За».
    // A case-sensitive indexOf dropped the mark and the count lost its proof.
    const text = 'Я шёл по лесу. За мной гналась собака, но я убежал.';
    const out = markUp(text, [ev('за мной гналась собака,')]);
    expect(out).toContain('<mark class="ev"');
    // Rendered from the ORIGINAL text — the user reads their own capital.
    expect(out).toContain('За мной гналась собака,');
  });

  it('folds ё to е the way the coder does', () => {
    const out = markUp('Он вёл меня домой.', [ev('он вел меня домой.')]);
    expect(out).toContain('<mark class="ev"');
    expect(out).toContain('вёл');
  });

  it('numbers each mark with its position in the ledger', () => {
    const text = 'Собака гналась. Я не смог убежать.';
    const out = markUp(text, [ev('собака гналась.'), ev('я не смог убежать.')]);
    expect(out).toContain('<sup>1</sup>');
    expect(out).toContain('<sup>2</sup>');
  });

  it('never lets two clauses claim the same span', () => {
    const text = 'Собака гналась за мной.';
    const out = markUp(text, [ev('собака гналась'), ev('собака гналась')]);
    expect(out.match(/<mark class="ev"/g)?.length).toBe(1);
  });

  it('leaves a genuine mismatch unmarked rather than guessing', () => {
    const out = markUp('Я шёл по лесу.', [ev('я плыл по реке.')]);
    expect(out).not.toContain('<mark');
    expect(out).toContain('Я шёл по лесу.');
  });

  it('escapes the text it did not mark', () => {
    const out = markUp('Мне снился <script>alert(1)</script>.', []);
    expect(out).not.toContain('<script>');
    expect(out).toContain('&lt;script&gt;');
  });
});
