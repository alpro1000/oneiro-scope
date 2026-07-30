import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'ru', 'de', 'es', 'fr'],
  defaultLocale: 'en'
});

export const config = {
  // Skip /api routes, /legal pages and static files from locale prefixing.
  // /legal/* are jurisdiction documents, not app screens: they must open at a
  // stable, unauthenticated, locale-less URL (privacy policy is a catalog
  // requirement and gets linked from outside), so the middleware never rewrites
  // them to /<locale>/legal/… and never runs the intl redirect on them.
  matcher: ['/((?!_next|api|legal|.*\\..*).*)']
};
