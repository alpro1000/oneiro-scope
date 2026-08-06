/**
 * The bit every view repeats: wire the bridge, wait, draw, report height.
 *
 * A view supplies two functions — how to recognise its payload in a tool
 * result, and how to turn that payload into HTML — and gets the whole MCP
 * Apps lifecycle for free. That is what makes "one more view" a file plus a
 * registry line rather than another copy of the boot sequence.
 */

import { HostBridge, type HostContext, type ToolResult } from './bridge';

export type Lang = 'ru' | 'en';

export interface ViewStrings {
  /** Shown before the host has sent anything. */
  waiting: string;
  /** Shown when a result arrived but carried nothing this view can draw. */
  empty: string;
}

export interface ViewSpec<P> {
  /** Pull this view's payload out of a tool result, or null if absent. */
  pick: (result: ToolResult) => P | null;
  /** Payload → HTML. `args` are the arguments the tool was called with. */
  render: (payload: P, lang: Lang, args: Record<string, unknown>) => string;
  strings: Record<Lang, ViewStrings>;
}

/**
 * Mark up an "explain this" control.
 *
 * `question` is the text handed to the chat verbatim, so it should carry the
 * figures rather than describe them: the model should be reading the same
 * numbers the user is pointing at, not a paraphrase of them.
 *
 * Rendered as a real <button>, so it is reachable by keyboard and announced
 * as a control — these are the only interactive elements in any view.
 */
export function askButton(question: string, label: string, strong = false): string {
  const cls = strong ? 'ask ask-strong' : 'ask';
  return `<button type="button" class="${cls}" data-ask="${esc(question)}">${esc(label)}</button>`;
}

export const ASK_LABEL: Record<Lang, string> = { ru: 'объяснить', en: 'explain' };

/** Locale from the payload if it says, else the document's. */
function langOf(payload: unknown): Lang {
  const l = (payload as { locale?: string } | null)?.locale;
  if (l === 'en' || l === 'ru') return l;
  return document.documentElement.lang === 'en' ? 'en' : 'ru';
}

/**
 * Read a JSON payload out of whichever shape the host used.
 *
 * `structuredContent` is the direct route. Hosts that only pass text blocks
 * still carry the same JSON, so both are tried before giving up — a view that
 * renders nothing because it looked in one place is indistinguishable from a
 * broken one.
 */
export function fromResult<P>(
  result: ToolResult,
  accept: (candidate: Record<string, unknown>) => P | null,
): P | null {
  const sc = result.structuredContent;
  if (sc && typeof sc === 'object') {
    const hit = accept(sc as Record<string, unknown>);
    if (hit) return hit;
  }
  for (const block of result.content ?? []) {
    const b = block as { type?: string; text?: string };
    if (b?.type !== 'text' || typeof b.text !== 'string') continue;
    try {
      const parsed = JSON.parse(b.text);
      if (parsed && typeof parsed === 'object') {
        const hit = accept(parsed as Record<string, unknown>);
        if (hit) return hit;
      }
    } catch {
      /* not JSON — try the next block */
    }
  }
  return null;
}

export function mountView<P>(spec: ViewSpec<P>): void {
  const root = document.getElementById('root');
  if (!root) throw new Error('view shell has no #root');

  const note = (text: string) => `<p class="note">${text}</p>`;
  let lang: Lang = document.documentElement.lang === 'en' ? 'en' : 'ru';

  // The arguments arrive BEFORE the result (the host sends tool-input as the
  // call starts), so by the time there is something to draw they are here.
  let args: Record<string, unknown> = {};

  const bridge = new HostBridge({
    onToolInput: (a) => { args = a ?? {}; },
    onToolResult: (result) => {
      const payload = spec.pick(result);
      lang = payload ? langOf(payload) : lang;
      root.innerHTML = payload
        ? spec.render(payload, lang, args)
        : note(spec.strings[lang].empty);
      bridge.reportSize();
    },
    onContext: (ctx: HostContext) => {
      if (ctx.theme) document.documentElement.dataset.theme = ctx.theme;
      bridge.reportSize();
    },
  });

  root.innerHTML = note(spec.strings[lang].waiting);

  bridge.initialize().then((ctx) => {
    if (ctx?.theme) document.documentElement.dataset.theme = ctx.theme;
    bridge.reportSize();
  });

  // One delegated listener rather than a handler per row: a natal chart can
  // carry sixty of these, and the markup is regenerated on every repaint.
  root.addEventListener('click', (ev) => {
    const el = (ev.target as HTMLElement | null)?.closest?.('[data-ask]');
    const question = el?.getAttribute('data-ask');
    if (question) bridge.ask(question);
  });

  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(() => bridge.reportSize()).observe(document.documentElement);
  }
}

/** Escape text destined for innerHTML. Every view renders user-derived text. */
export const esc = (s: string): string =>
  s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
