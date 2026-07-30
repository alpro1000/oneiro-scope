import {NextRequest, NextResponse} from 'next/server';
import {getLunarDay} from '../../../lib/lunar-server';

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
    // Honest failure, not a fabricated phase (conventions.md §12): a 502 with
    // no data, so the caller shows an error rather than an invented lunar day.
    console.error('Failed to load lunar data from backend.', error);
    return NextResponse.json(
      {date, locale, tz, error: 'Backend lunar service unavailable'},
      {status: 502}
    );
  }
}
