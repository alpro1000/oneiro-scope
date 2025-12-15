const createNextIntlPlugin = require('next-intl/plugin');

// Explicitly point to the request config to avoid auto-detection issues in App Router
const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000']
    }
  }
};

module.exports = withNextIntl(nextConfig);
