/**
 * Billing API client — Lemon Squeezy checkout + subscription summary.
 *
 * Talks to the backend `/api/v1/billing/*` endpoints. Checkout returns a
 * hosted Lemon Squeezy URL the caller redirects the browser to; we never
 * handle card data ourselves (Lemon is the Merchant of Record).
 */

import { resolveApiBase } from './api-base';
import { authHeaders } from './auth-client';

export type ProductSlug =
  | 'premium_monthly'
  | 'pro_monthly'
  | 'natal_pdf'
  | 'yearly_forecast';

export interface CheckoutResponse {
  url: string;
  checkout_id: string;
}

export interface SubscriptionSummary {
  tier: string; // free | premium | pro
  status: string | null;
  current_period_end: string | null;
  provider: string;
  cancel_at_period_end: boolean;
}

function billingApiBase(): string {
  const isServer = typeof window === 'undefined';
  return resolveApiBase({
    serviceName: 'Billing API',
    isServer,
    serverEnvVars: [process.env.BILLING_API_URL, process.env.NEXT_PUBLIC_API_URL],
    clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    relativeFallback: '/api',
  });
}

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

/**
 * Create a hosted checkout. Requires an authenticated user (401 otherwise).
 * Returns the Lemon Squeezy URL to redirect to.
 */
export async function createCheckout(params: {
  productSlug: ProductSlug;
  successRedirect?: string;
}): Promise<CheckoutResponse> {
  const url = `${billingApiBase()}/api/v1/billing/checkout`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({
      product_slug: params.productSlug,
      success_redirect: params.successRedirect || null,
    }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

/** Current subscription summary for the logged-in user. */
export async function getSubscription(): Promise<SubscriptionSummary> {
  const url = `${billingApiBase()}/api/v1/billing/me`;
  const response = await fetch(url, {
    headers: { Accept: 'application/json', ...authHeaders() },
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}
