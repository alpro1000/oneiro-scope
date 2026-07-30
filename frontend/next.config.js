const createNextIntlPlugin = require('next-intl/plugin');

// Explicitly point to the request config to avoid auto-detection issues in App Router
const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

// Origins allowed to invoke Server Actions. Local dev is always allowed;
// production origins (e.g. the Vercel domain) come from SERVER_ACTION_ORIGINS
// (comma-separated host[:port], no scheme) so the deploy target isn't hardcoded.
const serverActionOrigins = [
  'localhost:3000',
  ...(process.env.SERVER_ACTION_ORIGINS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // chart-kit ships TypeScript source (its `exports` points at src/index.ts);
  // Next must transpile it rather than expect pre-built JS. The package has no
  // runtime deps and only relative imports, so this is the whole integration.
  transpilePackages: ['@oneiroscope/chart-kit'],
  experimental: {
    serverActions: {
      allowedOrigins: serverActionOrigins
    }
  }
};

module.exports = withNextIntl(nextConfig);
