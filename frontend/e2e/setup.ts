/**
 * E2E test setup - must be imported at the top of each test file
 *
 * This ensures polyfills are loaded before Playwright initializes
 */

// Polyfill TransformStream for Playwright 1.57+ with MCP support
if (typeof globalThis.TransformStream === 'undefined') {
  const {TransformStream} = require('node:stream/web');
  globalThis.TransformStream = TransformStream;
}
