/**
 * The "explain" control is the seam between the deterministic layer and the
 * model's reading of it, so two things about it matter: the question must
 * carry the figures verbatim, and the attribute must survive text that looks
 * like markup.
 */
import { describe, expect, it } from 'vitest';
import { ASK_LABEL, askButton, esc } from '../src/view';

describe('askButton', () => {
  it('puts the question in data-ask, where the delegated listener reads it', () => {
    const html = askButton('Объясни: Sun ♋ 9°50′, орб 0.44°.', 'объяснить');
    expect(html).toContain('data-ask="Объясни: Sun ♋ 9°50′, орб 0.44°."');
    expect(html).toContain('>объяснить<');
  });

  it('is a real button, so it is keyboard-reachable and announced as a control', () => {
    expect(askButton('q', 'l')).toContain('<button type="button"');
  });

  it('escapes a quote in the question rather than breaking out of the attribute', () => {
    // Dream clauses are user text and reach this verbatim.
    const html = askButton('Объясни: «он сказал "нет"» <b>', 'l');
    expect(html).not.toContain('"нет"');
    expect(html).toContain('&quot;');
    expect(html).not.toContain('<b>');
  });

  it('draws the section-level ask as a button and the row-level one quietly', () => {
    expect(askButton('q', 'l')).toContain('class="ask"');
    expect(askButton('q', 'l', true)).toContain('class="ask ask-strong"');
  });

  it('labels both languages', () => {
    expect(ASK_LABEL.ru).toBe('объяснить');
    expect(ASK_LABEL.en).toBe('explain');
  });
});

describe('esc', () => {
  it('escapes the four characters that matter for innerHTML', () => {
    expect(esc('<b>"x" & y</b>')).toBe('&lt;b&gt;&quot;x&quot; &amp; y&lt;/b&gt;');
  });

  it('coerces a non-string instead of throwing', () => {
    // The regression: `part_of_fortune.dispositor` is a full placement object,
    // not a planet name. The declared type said string, esc() called .replace
    // on it, and the whole view went blank — a worse failure than printing the
    // value, and one that tells the reader nothing.
    expect(() => esc({ planet: 'saturn' } as unknown as string)).not.toThrow();
    expect(esc(undefined as unknown as string)).toBe('');
    expect(esc(null as unknown as string)).toBe('');
    expect(esc(7 as unknown as string)).toBe('7');
  });
});
