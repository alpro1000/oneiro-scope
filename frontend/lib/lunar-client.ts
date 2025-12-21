import {buildLunarUrl, resolveLunarApiBase} from './lunar-endpoint';
import type {LunarDayPayload} from './lunar-server';

/**
 * Fetch with exponential backoff retry logic.
 * Retries on network errors and 5xx responses.
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = 3,
  baseDelay = 1000
): Promise<Response> {
  let lastError: Error | null = null;

  // "retries" here really means attempts, so ensure we try at least once
  const attempts = Math.max(1, retries);

  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      const response = await fetch(url, options);

      // Retry on server errors (5xx)
      if (response.status >= 500 && attempt < attempts - 1) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }

      return response;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));

      // Don't retry on last attempt
      if (attempt < attempts - 1) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError ?? new Error('Failed to fetch after retries');
}

export async function fetchLunarDayClient(
  date: string,
  locale: string,
  timezone?: string,
  options?: {retries?: number; baseDelay?: number}
): Promise<LunarDayPayload> {
  const base = resolveLunarApiBase(false);
  const tz = timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'Europe/Moscow';
  const url = buildLunarUrl(base, {date, locale, tz});
  const response = await fetchWithRetry(
    url,
    {headers: {Accept: 'application/json'}},
    options?.retries ?? 3, // attempts
    options?.baseDelay ?? 1000 // 1s base delay
  );

  if (!response.ok) {
    throw new Error(`Lunar API responded with ${response.status}`);
  }

  return response.json();
}
