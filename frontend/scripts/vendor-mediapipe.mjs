// Vendors the MediaPipe tasks-vision WASM runtime from node_modules into
// public/ so the face scanner loads it SAME-ORIGIN at runtime.
//
// Why: the /face scanner used to pull the wasm from cdn.jsdelivr.net and the
// model from storage.googleapis.com at runtime. When either host is blocked
// for the visitor (region / network policy / privacy extension), the load
// rejects and the screen shows a raw "Load failed". Serving these assets from
// the app's own origin (which the visitor has already reached) removes that
// third-party dependency.
//
// The WASM is COPIED here (not committed) so it always matches the installed
// @mediapipe/tasks-vision version — committing it risks drift on upgrade, and
// it is ~19 MB. The model (.task) is committed under public/vendor/mediapipe/
// because it is not part of the npm package. This script runs from `predev`
// and `prebuild`, so the copy exists for both local dev and the Vercel build.
import {cpSync, existsSync, mkdirSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'node_modules/@mediapipe/tasks-vision/wasm');
const dest = join(root, 'public/vendor/mediapipe/wasm');

if (!existsSync(src)) {
  console.error(
    `[vendor-mediapipe] ${src} not found — is @mediapipe/tasks-vision installed?`,
  );
  process.exit(1);
}

mkdirSync(dest, {recursive: true});
cpSync(src, dest, {recursive: true});
console.log(`[vendor-mediapipe] copied WASM runtime -> ${dest}`);
