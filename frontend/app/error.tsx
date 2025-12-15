'use client';

import Link from 'next/link';
import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Frontend error boundary caught an error:', error);
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12 text-slate-100">
      <div className="max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-8 shadow-xl shadow-indigo-500/10">
        <p className="text-sm uppercase tracking-wide text-indigo-300">Service notice</p>
        <h1 className="mt-3 text-3xl font-semibold text-white">We&apos;re having trouble talking to the backend</h1>
        <p className="mt-4 text-slate-200">
          The frontend could not reach the API service. If you&apos;re deploying to Render, ensure the
          backend URL environment variables (NEXT_PUBLIC_API_URL, ASTROLOGY_API_URL, DREAMS_API_URL,
          LUNAR_API_URL) point to the Render external URL and redeploy the frontend.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={reset}
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400"
          >
            Retry
          </button>
          <Link
            href="/"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-indigo-400 hover:text-indigo-100"
          >
            Go home
          </Link>
        </div>
        {error.digest ? (
          <p className="mt-4 text-xs text-slate-400">Error digest: {error.digest}</p>
        ) : null}
      </div>
    </main>
  );
}
