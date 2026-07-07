/**
 * Synchronous inline script setting `data-theme` before first paint —
 * avoids a flash of the wrong theme between server render and the
 * ThemeToggle client component hydrating. No 'use client': this is a
 * plain script tag, not a hook.
 */
export default function ThemeInit() {
  const script = `
    (function () {
      try {
        var stored = localStorage.getItem('oneiro-theme');
        var theme = stored === 'dark' || stored === 'light'
          ? stored
          : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
      } catch (e) {}
    })();
  `;
  // eslint-disable-next-line react/no-danger
  return <script dangerouslySetInnerHTML={{__html: script}} />;
}
