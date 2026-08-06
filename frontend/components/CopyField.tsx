'use client';

/**
 * A value with a copy button — the connector URL, mainly.
 *
 * The whole point of the connect page is that someone pastes this string into
 * another app's settings dialog. Making them select it by hand on a phone is
 * where the flow breaks, so the copy is one tap and says so when it worked.
 */

import { useEffect, useState } from 'react';

interface Props {
  value: string;
  copyLabel: string;
  copiedLabel: string;
  /** Shown instead of the button when the value is not configured. */
  unavailable?: string;
}

export default function CopyField({ value, copyLabel, copiedLabel, unavailable }: Props) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const id = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(id);
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // Clipboard is blocked without a secure context or user permission.
      // Selecting the text is the fallback that always works, so do that
      // rather than claiming a copy that did not happen.
      const el = document.getElementById('connector-url');
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
      }
    }
  }

  if (!value) {
    return <div className="copy-field"><code className="copy-value">{unavailable ?? '—'}</code></div>;
  }

  return (
    <div className="copy-field">
      <code className="copy-value" id="connector-url">{value}</code>
      <button type="button" className="copy-btn" onClick={copy}>
        {copied ? copiedLabel : copyLabel}
      </button>
    </div>
  );
}
