import {render, screen, waitFor} from '@testing-library/react';
import LunarInstrument from '@/components/LunarInstrument';
import type {LunarDayPayload} from '@/lib/lunar-server';

describe('LunarInstrument', () => {
  const baseDay: LunarDayPayload = {
    date: '2024-05-14',
    lunar_day: 6,
    phase: 'Waxing Crescent',
    description: 'Intuitive dreams tonight',
    recommendation: 'Write down subtle details and emotions.',
    locale: 'en',
    source: 'test-suite',
    timezone: 'Europe/Moscow',
    illumination: 0.42,
    phase_key: 'waxing_crescent',
    ephemeris_engine: 'SWIEPH',
    jd_ut: 2460444.5
  };

  afterEach(() => jest.restoreAllMocks());

  it('renders the selected lunar day summary', () => {
    jest.spyOn(global, 'fetch').mockImplementation(
      async () => new Response(JSON.stringify(baseDay), {headers: {'Content-Type': 'application/json'}})
    );

    render(<LunarInstrument initial={baseDay} locale="en" defaultTz="Europe/Moscow" />);

    expect(screen.getByText(baseDay.description)).toBeInTheDocument();
    expect(screen.getByText(baseDay.recommendation)).toBeInTheDocument();
    // phase name (from the server) is shown next to waxing/waning
    expect(screen.getByText(/Waxing Crescent/)).toBeInTheDocument();
  });

  it('marks today and loads the month day-by-day (no fabrication)', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockImplementation(
      async (input: RequestInfo | URL | Request) => {
        const href = typeof input === 'string' ? input : 'url' in input ? input.url : String(input);
        const url = new URL(href, 'http://localhost');
        const date = url.searchParams.get('date') ?? baseDay.date;
        return new Response(
          JSON.stringify({...baseDay, date, lunar_day: Number(date.split('-')[2])}),
          {headers: {'Content-Type': 'application/json'}}
        );
      }
    );

    render(<LunarInstrument initial={baseDay} locale="en" defaultTz="Europe/Moscow" />);

    // The whole month is present as cells, and today is flagged from the SSR payload.
    expect(screen.getByTestId('day-2024-05-01')).toBeInTheDocument();
    expect(screen.getByTestId('day-2024-05-31')).toBeInTheDocument();
    expect(screen.getByTestId('day-2024-05-14')).toHaveAttribute('aria-current', 'date');

    // Each day is fetched from the server — never invented client-side.
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });
});
