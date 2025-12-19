import {NextResponse} from 'next/server';
import {resolveLunarApiBase} from '../../../lib/lunar-endpoint';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const base = resolveLunarApiBase(true);
    const url = `${base}/api/v1/lunar/timezones`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    let response: Response;
    try {
      response = await fetch(url, {
        headers: {Accept: 'application/json'},
        next: {revalidate: 3600}, // Cache for 1 hour
        signal: controller.signal
      });
    } finally {
      clearTimeout(timeout);
    }

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch timezones from backend:', error);

    // Fallback to minimal timezone list
    return NextResponse.json({
      timezones: [
        {value: 'Europe/Moscow', label: 'Москва (UTC+3)', region: 'Европа', utc_offset: '+03:00'},
        {value: 'Europe/Kiev', label: 'Киев (UTC+2)', region: 'Европа', utc_offset: '+02:00'},
        {value: 'Asia/Almaty', label: 'Алматы (UTC+6)', region: 'Азия', utc_offset: '+06:00'},
        {value: 'Europe/Berlin', label: 'Берлин (UTC+1)', region: 'Европа', utc_offset: '+01:00'},
        {value: 'America/New_York', label: 'Нью-Йорк (UTC-5)', region: 'Америка', utc_offset: '-05:00'},
        {value: 'UTC', label: 'UTC', region: 'Общее', utc_offset: '+00:00'},
      ]
    });
  }
}
