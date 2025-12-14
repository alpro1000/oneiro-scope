const DEFAULT_BASE = 'http://localhost:8000/api/v1/lunar';
const RELATIVE_BASE = '/api/lunar';

function normalizeBase(rawBase: string): string {
  const trimmed = rawBase.trim();
  if (!trimmed) return trimmed;

  const stripped = trimmed.replace(/\/$/, '');

  // If a host is provided without a protocol, assume HTTPS for Render services.
  if (!stripped.startsWith('http') && !stripped.startsWith('/')) {
    return normalizeBase(`https://${stripped}`);
  }

  // If a specific lunar path is already provided, trust it.
  if (stripped.endsWith('/lunar')) {
    return stripped;
  }

  // Otherwise, append the backend-friendly path used by the FastAPI service.
  return `${stripped}/api/v1/lunar`;
}

export function resolveLunarApiBase(isServer: boolean): string {
  if (isServer) {
    const envBase =
      process.env.LUNAR_API_URL ||
      process.env.NEXT_PUBLIC_LUNAR_API_URL ||
      process.env.NEXT_PUBLIC_API_URL;
    if (envBase) {
      return normalizeBase(envBase);
    }
    return DEFAULT_BASE;
  }

  const clientBase = process.env.NEXT_PUBLIC_LUNAR_API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (clientBase) {
    return normalizeBase(clientBase);
  }

  return RELATIVE_BASE;
}

export function buildLunarUrl(base: string, params: Record<string, string>): string {
  if (base.startsWith('http')) {
    const url = new URL(base);
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
    return url.toString();
  }

  const search = new URLSearchParams(params);
  return `${base}?${search.toString()}`;
}
