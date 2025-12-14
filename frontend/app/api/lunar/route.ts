import {NextRequest, NextResponse} from 'next/server';
import {getLunarDay} from '../../../lib/lunar-server';

const MOCK_FALLBACK = {
  phase: 'Full Moon',
  phase_key: 'Full',
  description: 'Mock data: a night for celebrating completed cycles and intuitive insights.',
  recommendation: 'Share your reflections, record vivid dreams, and rest under the bright moon.',
  source: 'mock'
} as const;

function resolveDate(searchParams: URLSearchParams): string {
  const param = searchParams.get('date');
  if (param && /^\d{4}-\d{2}-\d{2}$/.test(param)) {
    return param;
  }
  return new Date().toISOString().slice(0, 10);
}

function resolveLocale(searchParams: URLSearchParams): string {
  return searchParams.get('locale') ?? 'en';
}

function resolveTimezone(searchParams: URLSearchParams): string | undefined {
  return searchParams.get('tz') ?? undefined;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const date = resolveDate(searchParams);
  const locale = resolveLocale(searchParams);
  const tz = resolveTimezone(searchParams);

  try {
    const payload = await getLunarDay({date, locale, tz});
    return NextResponse.json({...payload, source: payload.source ?? 'backend'});
  } catch (error) {
    console.error('Failed to load lunar data, falling back to mock payload.', error);
    return NextResponse.json(
      {
        date,
        lunar_day: 15,
        locale,
        ...MOCK_FALLBACK
      },
      {status: 200}
    );
  }
}
