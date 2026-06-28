/**
 * Auth API client + browser token storage.
 *
 * Talks to the backend `/api/v1/auth/*` endpoints (register, login, me).
 * The access token is kept in localStorage (client-only) — these helpers
 * are no-ops on the server so they're safe to import from RSC modules.
 */

import { resolveApiBase } from './api-base';

const TOKEN_KEY = 'oneiro_token';

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
  language: string;
}

export interface UserMe {
  id: string;
  email: string | null;
  name: string | null;
  language: string;
  timezone: string;
  tier: string;
  is_verified: boolean;
}

function authApiBase(): string {
  const isServer = typeof window === 'undefined';
  return resolveApiBase({
    serviceName: 'Auth API',
    isServer,
    serverEnvVars: [process.env.AUTH_API_URL, process.env.NEXT_PUBLIC_API_URL],
    clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    relativeFallback: '/api',
  });
}

// ---------- Token storage (browser only) ----------------------------------

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------- API calls ------------------------------------------------------

async function readError(response: Response): Promise<string> {
  const data = await response.json().catch(() => null);
  if (!data) return `API error: ${response.status}`;
  const detail = data.detail ?? data.error ?? data;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    return detail.error || JSON.stringify(detail);
  }
  return `API error: ${response.status}`;
}

export async function register(params: {
  email: string;
  password: string;
  name?: string;
  language?: string;
}): Promise<TokenResponse> {
  const url = `${authApiBase()}/api/v1/auth/register`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      email: params.email,
      password: params.password,
      name: params.name || null,
      language: params.language || 'en',
    }),
  });
  if (!response.ok) throw new Error(await readError(response));
  const token = (await response.json()) as TokenResponse;
  setToken(token.access_token);
  return token;
}

export async function login(params: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const url = `${authApiBase()}/api/v1/auth/login`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error(await readError(response));
  const token = (await response.json()) as TokenResponse;
  setToken(token.access_token);
  return token;
}

export async function fetchMe(): Promise<UserMe> {
  const url = `${authApiBase()}/api/v1/auth/me`;
  const response = await fetch(url, {
    headers: { Accept: 'application/json', ...authHeaders() },
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export function logout(): void {
  clearToken();
}
