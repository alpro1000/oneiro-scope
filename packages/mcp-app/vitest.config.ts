/**
 * Vitest needs the same two aliases the bundle is built with.
 *
 * Without them a test that imports a view module fails to RESOLVE rather than
 * to assert — and `vitest run` reports that as a failed suite with zero tests,
 * which is easy to read as "nothing to run here". The three places that must
 * agree are this file, `build.mjs`'s esbuild `alias`, and `tsconfig.json`'s
 * `paths`; only the first two affect what actually runs.
 */
import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';

const REPO = resolve(import.meta.dirname, '../..');

export default defineConfig({
  resolve: {
    alias: {
      '@oneiroscope/chart-kit': resolve(REPO, 'packages/chart-kit/src/index.ts'),
      '@frontend/world-coast': resolve(REPO, 'frontend/lib/world-coast.ts'),
    },
  },
});
