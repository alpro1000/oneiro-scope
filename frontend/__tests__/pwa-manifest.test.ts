/**
 * The PWA promises files exist. This checks that they do.
 *
 * A manifest entry pointing at a missing icon fails silently in the
 * worst way: the browser installs the app anyway and shows a blank or
 * generic tile, and nobody notices until someone tries to add it to a
 * home screen on a real phone. Same class of failure for the service
 * worker's shell list — `cache.add` on a 404 is swallowed (deliberately,
 * so one bad entry cannot void the whole cache), which means a typo
 * there costs offline support with no error anywhere.
 *
 * Regenerate the icons with `python3 scripts/generate_pwa_icons.py`.
 */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const resolvePublic = (url: string) => path.join(PUBLIC_DIR, url.replace(/^\//, ''));

type ManifestIcon = { src: string; sizes: string; type: string; purpose?: string };

const manifest = JSON.parse(
  readFileSync(path.join(PUBLIC_DIR, 'manifest.json'), 'utf8'),
) as { icons: ManifestIcon[]; start_url: string };

/** Width and height straight out of the PNG's IHDR chunk. */
function pngSize(file: string): { width: number; height: number } {
  const buf = readFileSync(file);
  expect(buf.subarray(0, 8)).toEqual(
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  );
  expect(buf.subarray(12, 16).toString('ascii')).toBe('IHDR');
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

describe('every icon the manifest declares', () => {
  it.each(manifest.icons.map((i) => [i.src, i] as const))('%s exists', (_src, icon) => {
    expect(existsSync(resolvePublic(icon.src))).toBe(true);
  });

  it.each(manifest.icons.map((i) => [i.src, i] as const))(
    '%s really is the size it claims',
    (_src, icon) => {
      const [w, h] = icon.sizes.split('x').map(Number);
      expect(pngSize(resolvePublic(icon.src))).toEqual({ width: w, height: h });
    },
  );

  it('includes a maskable variant', () => {
    // Without one, Android crops the "any" icon to its platform shape and
    // can cut into the mark. The maskable file draws the same mark
    // smaller so no crop shape reaches it.
    expect(manifest.icons.some((i) => i.purpose === 'maskable')).toBe(true);
  });
});

describe('the service worker shell', () => {
  const sw = readFileSync(path.join(PUBLIC_DIR, 'sw.js'), 'utf8');
  const shell = sw
    .slice(sw.indexOf('const SHELL = ['), sw.indexOf('];', sw.indexOf('const SHELL = [')))
    .match(/'([^']+)'/g)!
    .map((s) => s.slice(1, -1));

  it('lists something to cache', () => {
    expect(shell.length).toBeGreaterThan(3);
  });

  it.each(shell.filter((u) => u !== '/'))('%s exists to be cached', (url) => {
    // '/' is served by Next, not by a file in public/, so it is excluded.
    expect(existsSync(resolvePublic(url))).toBe(true);
  });
});
