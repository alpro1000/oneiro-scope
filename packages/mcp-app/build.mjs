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
  { entry: 'src/acg-map.ts', out: 'acg-map.html', title: 'Astrocartography' },
  { entry: 'src/lunar-month.ts', out: 'lunar-month.html', title: 'Lunar calendar' },
  { entry: 'src/dream-evidence.ts', out: 'dream-evidence.html', title: 'Dream coding' },
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

/* --- "explain" controls: the seam between the computed layer and the model's
   ---  reading of it.
   ---
   ---  Per-row controls are QUIET text, not outlined boxes. A natal chart
   ---  carries thirty of them, and thirty brass rectangles fight the numbers
   ---  they sit next to — the design system's rule that emphasis must not
   ---  compete with data. Only the section-level "read this as a whole" is
   ---  drawn as a button, because there is exactly one of it per panel. */
.ask{
  background:transparent;border:0;padding:0;cursor:pointer;
  font-family:var(--font-ui);font-size:11px;letter-spacing:.02em;
  color:var(--muted);border-bottom:1px solid transparent;
  transition:color .15s ease,border-color .15s ease;
}
.ask:hover{color:var(--brass);border-bottom-color:var(--brass-dim)}
.ask:focus-visible{outline:2px solid var(--brass);outline-offset:2px}
.ask-strong{
  border:1px solid var(--brass-dim);color:var(--brass);padding:5px 10px;
  font-size:12px;width:100%;text-align:center;
}
.ask-strong:hover{background:var(--brass);color:var(--abyss);border-bottom-color:var(--brass-dim)}
.ask-cell{text-align:right;white-space:nowrap;padding-left:10px}
.asp .ask{margin-top:3px}
.ev-row .ask{margin-top:5px;margin-left:2.1em}
.lday .ask{margin-top:6px}
.lg .ask{margin-left:5px;font-size:10px}
.ask-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-top:11px;
  padding-top:10px;border-top:1px solid var(--grat-1)}
.ask-row .ask-strong{width:auto}
.ask-hint{font-family:var(--font-ui);font-size:11px;color:var(--dim);line-height:1.5;
  margin:7px 0 0;display:block}
.ask-row .ask-hint{margin:0;flex:1;min-width:14ch}
section > .ask-strong{margin-top:10px}
@media (prefers-reduced-motion: reduce){.ask{transition:none}}

/* --- shared page furniture ------------------------------------------------ */
.head{margin-bottom:14px}
h1{font-family:var(--font-display);font-weight:400;letter-spacing:-.015em;
  line-height:1.02;font-size:clamp(22px,3.4vw,32px);margin:6px 0 0}
.lede{color:var(--muted);font-size:13.5px;line-height:1.6;margin:8px 0 0;max-width:62ch}
.head .eyebrow{margin-bottom:0}

/* --- astrocartography ----------------------------------------------------- */
svg{display:block;width:100%;height:auto;border:1px solid var(--grat-2)}
.legend{margin-top:12px;border:1px solid var(--grat-2);background:var(--panel);padding:11px 13px}
.lgs{display:flex;flex-wrap:wrap;gap:6px 14px;margin-bottom:9px}
.lg{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.lg i{width:13px;height:2px;display:inline-block}
.kinds{display:flex;flex-wrap:wrap;gap:5px 18px;font-size:11.5px;color:var(--dim);
  padding-top:8px;border-top:1px solid var(--grat-1)}
.kinds span{display:inline-flex;align-items:center;gap:6px}
.k{width:16px;height:0;border-top:1.4px solid var(--muted);display:inline-block}
.k.dashed{border-top-style:dashed}
.k.dotted{border-top-style:dotted}

/* --- lunar calendar ------------------------------------------------------- */
.lgrid{display:grid;gap:1px;background:var(--grat-1);
  grid-template-columns:repeat(auto-fill,minmax(132px,1fr));border:1px solid var(--grat-2)}
.lday{background:var(--panel);padding:9px 10px}
.lday-top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.lday-date{font-size:10.5px;color:var(--dim)}
.lday-n{font-size:19px;color:var(--brass);margin-top:4px;line-height:1.1}
.lday-n .dim{font-size:10.5px}
.lday-phase{font-size:11.5px;color:var(--muted);margin-top:2px}
.lday-illum{font-size:11.5px;margin-top:3px}
.lday-illum .dim{font-size:10px}
.lday-sign{font-size:11.5px;color:var(--muted);margin-top:2px}
.lday-start{font-size:10.5px;margin-top:2px}

/* --- dream coding --------------------------------------------------------- */
.dream{font-size:14.5px;line-height:1.85;color:var(--parchment);margin:0;max-width:66ch}
mark.ev{background:transparent;color:var(--parchment);
  border-bottom:2px solid var(--brass);padding-bottom:1px}
mark.ev sup{font-family:var(--font-data);font-size:9.5px;color:var(--brass);
  margin-left:2px;vertical-align:super}
.ev-row{padding:8px 0;border-bottom:1px solid var(--grat-1)}
.ev-row:last-child{border-bottom:0}
.ev-head{display:flex;align-items:baseline;gap:7px;font-size:12.5px}
.ev-n{color:var(--brass);min-width:1.4em}
.ev-cat{color:var(--parchment)}
.ev-conf{margin-left:auto;color:var(--dim);font-size:11px}
.ev-quote{font-size:13px;color:var(--muted);margin:3px 0 0;padding-left:2.1em;line-height:1.5}
.ev-meta,.ev-src{font-size:11px;padding-left:2.1em;margin-top:2px}
.deg{margin:0;padding-left:17px;font-size:11.5px;color:var(--notice-ink)}
.deg li{margin-bottom:3px}
.llm{margin-top:14px}
.prose{font-size:13.5px;line-height:1.7;color:var(--muted);margin:9px 0 0;max-width:66ch;
  white-space:pre-wrap}
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
    alias: {
      '@oneiroscope/chart-kit': resolve(REPO, 'packages/chart-kit/src/index.ts'),
      // One copy of the coastline, shared with the Next app.
      '@frontend/world-coast': resolve(REPO, 'frontend/lib/world-coast.ts'),
    },
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
