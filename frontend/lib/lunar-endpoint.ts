const DEFAULT_BASE = 'http://localhost:8000/lunar';
const RELATIVE_BASE = '/api/lunar';

export function resolveLunarApiBase(isServer: boolean): string {
  if (isServer) {
    return process.env.LUNAR_API_URL ?? process.env.NEXT_PUBLIC_LUNAR_API_URL ?? DEFAULT_BASE;
  }
  return process.env.NEXT_PUBLIC_LUNAR_API_URL ?? RELATIVE_BASE;
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
