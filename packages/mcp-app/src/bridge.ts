/**
 * MCP Apps host bridge — JSON-RPC 2.0 over `postMessage`.
 *
 * Implements the view half of the `io.modelcontextprotocol/ui` extension
 * (ext-apps specification 2026-01-26, folded into the 2026-07-28 MCP
 * specification). The host renders this view in a sandboxed iframe and speaks
 * JSON-RPC to it through `window.parent.postMessage`.
 *
 * What the view does here:
 *   → `ui/initialize`                      handshake, learns theme and size
 *   ← `ui/notifications/tool-input`        the arguments the tool was called with
 *   ← `ui/notifications/tool-result`       the payload to render
 *   ← `ui/notifications/host-context-changed`  theme / display-mode changes
 *   → `ui/notifications/size-changed`      so the host can size the iframe
 *   → `ui/message`                         hand a question back to the chat
 *
 * `ui/message` is the hinge of the whole product, not a convenience. The
 * numbers a view draws are the deterministic layer (1.0); what they MEAN is
 * the model's layer (0.7) and must be labelled as such. A button that puts
 * the exact figures back into the conversation and asks for them to be read
 * is that seam made literal: the user points at one aspect, one line, one
 * coded clause, and the model answers about THAT — with the orb and the
 * source in front of it instead of a paraphrase.
 *
 * Deliberately NOT used: `tools/call`, `resources/read`, `ui/open-link`,
 * `ui/update-model-context`. Every OneiroScope view derives everything it
 * draws from what it was handed, locally — so it never calls back for data.
 * That is what lets the resource ship with no declared CSP domains at all:
 * `connect-src 'none'` is enough, the host has nothing to warn the user
 * about, and the view cannot exfiltrate a birth time even if its code were
 * tampered with. `ui/message` does not weaken that: it goes to the host, in
 * the open, as a visible turn in the conversation.
 */

export interface HostContext {
  theme?: 'light' | 'dark';
  displayMode?: 'inline' | 'fullscreen' | 'pip';
  containerDimensions?: { width?: number; maxHeight?: number };
  styles?: { variables?: Record<string, string> };
  /** BCP-47 tag when the host sends one. Only the primary subtag is used. */
  locale?: string;
}

export interface ToolResult {
  content?: unknown[];
  structuredContent?: Record<string, unknown>;
}

type Handler = {
  onToolResult?: (result: ToolResult) => void;
  /**
   * The arguments the tool was called with.
   *
   * Worth having on its own: the dream view highlights the coded clauses
   * inside the dream TEXT, and the server never echoes that text back — it
   * would be a pointless round trip of the user's own words. The host already
   * holds the arguments and hands them over, so the text reaches the view
   * without the server ever repeating it.
   */
  onToolInput?: (args: Record<string, unknown>) => void;
  onContext?: (ctx: HostContext) => void;
};

const PROTOCOL_VERSION = '2026-01-26';

export class HostBridge {
  private nextId = 1;
  private handler: Handler;
  private lastSize = { width: 0, height: 0 };

  constructor(handler: Handler) {
    this.handler = handler;
    window.addEventListener('message', (ev) => this.receive(ev));
  }

  /** Handshake. Resolves with the host context, or null if the host is silent. */
  initialize(timeoutMs = 4000): Promise<HostContext | null> {
    const id = this.nextId++;
    return new Promise((resolve) => {
      let settled = false;
      const done = (ctx: HostContext | null) => {
        if (settled) return;
        settled = true;
        window.removeEventListener('message', listener);
        resolve(ctx);
      };
      const listener = (ev: MessageEvent) => {
        const msg = ev.data;
        if (!msg || msg.jsonrpc !== '2.0' || msg.id !== id) return;
        done((msg.result?.hostContext as HostContext) ?? {});
      };
      window.addEventListener('message', listener);
      this.send({
        jsonrpc: '2.0',
        id,
        method: 'ui/initialize',
        params: {
          capabilities: {},
          clientInfo: { name: 'oneiroscope-view', version: '0.1.0' },
          protocolVersion: PROTOCOL_VERSION,
        },
      });
      // Opened directly (a browser tab, a test) rather than by a host: stop
      // waiting and let the caller render whatever it can. Silence is a
      // legitimate state, not an error.
      window.setTimeout(() => done(null), timeoutMs);
    });
  }

  /** Tell the host how tall we are, so the iframe is not clipped or padded. */
  reportSize(): void {
    const el = document.documentElement;
    const width = Math.ceil(el.scrollWidth);
    const height = Math.ceil(el.scrollHeight);
    if (width === this.lastSize.width && height === this.lastSize.height) return;
    this.lastSize = { width, height };
    this.send({
      jsonrpc: '2.0',
      method: 'ui/notifications/size-changed',
      params: { width, height },
    });
  }

  /**
   * Put a question into the chat, as if the user had typed it.
   *
   * The text carries the figures verbatim rather than a summary — the point
   * is that the model reads the same numbers the user is looking at.
   */
  ask(text: string): void {
    this.send({
      jsonrpc: '2.0',
      id: this.nextId++,
      method: 'ui/message',
      params: { role: 'user', content: { type: 'text', text } },
    });
  }

  private receive(ev: MessageEvent): void {
    const msg = ev.data;
    if (!msg || msg.jsonrpc !== '2.0' || typeof msg.method !== 'string') return;
    switch (msg.method) {
      case 'ui/notifications/tool-input':
        this.handler.onToolInput?.((msg.params ?? {}).arguments ?? {});
        break;
      case 'ui/notifications/tool-result':
        this.handler.onToolResult?.(msg.params ?? {});
        break;
      case 'ui/notifications/host-context-changed':
        this.handler.onContext?.(msg.params ?? {});
        break;
      case 'ui/resource-teardown':
        // Request/response: acknowledge so the host is not left waiting.
        if (msg.id !== undefined) {
          this.send({ jsonrpc: '2.0', id: msg.id, result: {} });
        }
        break;
      default:
        break; // Unknown notifications are ignored by design.
    }
  }

  private send(message: unknown): void {
    // '*' is what the spec's examples use: the view cannot know the host's
    // origin, and the iframe is sandboxed with the host controlling the CSP.
    window.parent.postMessage(message, '*');
  }
}
