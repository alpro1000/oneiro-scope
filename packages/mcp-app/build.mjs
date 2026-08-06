/**
 * Build the MCP App views into self-contained HTML.
 *
 * Output goes to `backend/mcp/apps/dist/`, which the Python server reads and
 * serves as `ui://` resources. The bundle is committed, because the backend is
 * deployed by pip install with no Node step — and because it is committed, CI
 * runs `--check` to prove the committed file still matches the source. That is
 * the same trap as the old PWA bundle: tests pass against src while production
 * loads a stale artefact.
 *
 * Everything is inlined. The Google Fonts @import in tokens.css is deliberately
 * NOT carried over: under the MCP Apps default CSP (`default-src 'none'`) it
 * would be blocked, and declaring fonts.googleapis.com would make the host warn
 * the user about a view reaching an external domain. The three type ROLES
 * survive through the fallback stacks; only the exact faces differ. A birth
 * time is worth more than a typeface.
 */

import { build } from 'esbuild';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '../..');
const OUT_DIR = resolve(REPO, 'backend/mcp/apps/dist');

const VIEWS = [
  { entry: 'src/natal-wheel.ts', out: 'natal-wheel.html', title: 'Natal wheel' },
];

/** Design tokens, minus anything that would need the network. */
async function tokens() {
  const css = await readFile(resolve(REPO, 'frontend/styles/tokens.css'), 'utf8');
  return css
    .replace(/@import\s+url\([^)]*\);?/g, '')
    .trim();
}

const SHELL = (title, css, js) => `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} · OneiroScope</title>
<style>${css}</style>
</head>
<body><div id="root"></div><script>${js}</script></body>
</html>
`;

const VIEW_CSS = `
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--abyss);color:var(--parchment);
  font-family:var(--font-ui);font-size:14px}
body{padding:14px}
.wrap{display:grid;gap:16px;grid-template-columns:minmax(0,1fr) minmax(0,300px);align-items:start}
@media (max-width:720px){.wrap{grid-template-columns:1fr}}
.wheel{color:var(--parchment)}
.wheel svg{display:block;width:100%;height:auto}
.panels{display:grid;gap:14px}
section{border:1px solid var(--grat-2);background:var(--panel);padding:11px 13px}
.eyebrow{font-family:var(--font-data);font-size:10.5px;letter-spacing:.22em;
  text-transform:uppercase;color:var(--brass);margin-bottom:8px}
.kv{display:flex;justify-content:space-between;gap:12px;padding:3px 0;
  font-size:12.5px;color:var(--muted)}
.kv b{font-weight:400;color:var(--parchment)}
table{width:100%;border-collapse:collapse}
td{padding:3px 0;font-size:12.5px;vertical-align:baseline;border-bottom:1px solid var(--grat-1)}
tr:last-child td{border-bottom:0}
.num{font-family:var(--font-data);color:var(--parchment);text-align:right;white-space:nowrap}
.body{color:var(--muted)}
.dim{color:var(--dim)}
.glyph{font-size:15px;width:1.6em}
.flag{color:var(--brass);margin-left:5px}
.note{border:1px solid var(--brass-dim);background:var(--notice-bg);color:var(--notice-ink);
  padding:9px 11px;font-size:12.5px;line-height:1.55;margin:0}
.prov{display:flex;flex-wrap:wrap;gap:5px 22px;margin-top:14px;padding-top:10px;
  border-top:1px solid var(--grat-1);font-family:var(--font-data);font-size:11px;color:var(--parchment)}
.prov b{font-weight:400;color:var(--muted)}
.asp{padding:5px 0;border-bottom:1px solid var(--grat-1)}
.asp:last-child{border-bottom:0}
.asp-pair{font-size:12.5px;color:var(--muted)}
.asp-num{font-size:11.5px;text-align:left;margin-top:1px}
.disclaimer{color:var(--muted);font-size:12.5px;line-height:1.6;margin:11px 0 0;max-width:64ch}
.disclaimer b{color:var(--parchment);font-weight:500}
`;

async function renderView(view) {
  const result = await build({
    entryPoints: [resolve(HERE, view.entry)],
    bundle: true,
    format: 'iife',
    target: 'es2020',
    minify: true,
    write: false,
    absWorkingDir: HERE,
    // chart-kit is source-only (main points at src/index.ts); esbuild follows
    // it through the workspace symlink and inlines it — ~10 kB minified.
    alias: { '@oneiroscope/chart-kit': resolve(REPO, 'packages/chart-kit/src/index.ts') },
  });
  const js = result.outputFiles[0].text;
  const css = `${await tokens()}\n${VIEW_CSS}`;
  return SHELL(view.title, css, js);
}

const sha = (s) => createHash('sha256').update(s, 'utf8').digest('hex').slice(0, 12);

/**
 * esbuild strips types without checking them, and this bundle has no other
 * gate in front of it. The first version of the natal view called
 * `wheelLayout(core, {size})` where the signature is `(core, lat, lon, opts)`;
 * it built cleanly, shipped, and drew a wheel of NaN coordinates. tsc catches
 * that in a second, so the build refuses to produce a bundle without it.
 */
function typecheck() {
  execFileSync('npx', ['tsc', '--noEmit'], { cwd: HERE, stdio: 'inherit' });
}

async function main() {
  const check = process.argv.includes('--check');
  typecheck();
  await mkdir(OUT_DIR, { recursive: true });

  let stale = [];
  for (const view of VIEWS) {
    const html = await renderView(view);
    const target = resolve(OUT_DIR, view.out);
    if (check) {
      let current = '';
      try {
        current = await readFile(target, 'utf8');
      } catch {
        current = '';
      }
      if (current !== html) {
        stale.push(`${view.out} (committed ${sha(current)} != built ${sha(html)})`);
      }
      continue;
    }
    await writeFile(target, html, 'utf8');
    const kb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(1);
    console.log(`  ${view.out}  ${kb} kB  ${sha(html)}`);
  }

  if (check && stale.length) {
    console.error(
      'MCP App bundles are stale:\n  ' + stale.join('\n  ')
      + "\n\nRun `npm run build` in packages/mcp-app and commit the result.",
    );
    process.exit(1);
  }
  if (check) console.log('MCP App bundles match their source.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
