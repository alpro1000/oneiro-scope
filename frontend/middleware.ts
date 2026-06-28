import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'ru', 'de', 'es', 'fr'],
  defaultLocale: 'en'
});

export const config = {
  // Skip /api routes and static files from locale prefixing
  matcher: ['/((?!_next|api|.*\\..*).*)']
};
