const LOCALHOST_FALLBACK = 'http://localhost:8000';

export function normalizeBaseUrl(rawBase: string): string {
  const trimmed = rawBase.trim();
  if (!trimmed) return trimmed;

  const stripped = trimmed.replace(/\/$/, '');

  if (!stripped.startsWith('http') && !stripped.startsWith('/')) {
    return normalizeBaseUrl(`https://${stripped}`);
  }

  return stripped;
}

interface ResolveApiBaseOptions {
  serviceName: string;
  isServer: boolean;
  serverEnvVars: Array<string | undefined>;
  clientEnvVars: Array<string | undefined>;
  relativeFallback?: string;
}

export function resolveApiBase({
  serviceName,
  isServer,
  serverEnvVars,
  clientEnvVars,
  relativeFallback = '/api',
}: ResolveApiBaseOptions): string {
  const candidates = isServer ? serverEnvVars : clientEnvVars;
  const base = candidates.find((value) => value && value.trim());

  if (base) {
    return normalizeBaseUrl(base);
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error(
      `${serviceName} base URL is not configured. Set NEXT_PUBLIC_API_URL or a service-specific URL.`,
    );
  }

  if (isServer) {
    return LOCALHOST_FALLBACK;
  }

  return relativeFallback ?? LOCALHOST_FALLBACK;
}
