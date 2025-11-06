import {render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {NextIntlProvider} from 'next-intl';
import LunarWidget from '@/components/LunarWidget';
import type {LunarDayPayload} from '@/lib/lunar-server';
import messages from '../messages/en.json';

describe('LunarWidget', () => {
  const baseDay: LunarDayPayload = {
    date: '2024-05-14',
    lunar_day: 6,
    phase: 'Waxing Crescent',
    description: 'Intuitive dreams',
    recommendation: 'Write down subtle details and emotions.',
    locale: 'en',
    source: 'test-suite'
  };

  it('renders the current lunar day summary', () => {
    render(
      <NextIntlProvider locale="en" messages={messages}>
        <LunarWidget initialData={baseDay} locale="en" />
      </NextIntlProvider>
    );

    expect(screen.getByText(baseDay.phase)).toBeInTheDocument();
    expect(screen.getByText(messages.LunarWidget.recommendation)).toBeInTheDocument();
  });

  it('loads and displays the month table on demand', async () => {
    const user = userEvent.setup();
    const fetchMock = jest.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL | Request) => {
      const href = typeof input === 'string' ? input : 'url' in input ? input.url : input.toString();
      const url = new URL(href, 'http://localhost');
      const date = url.searchParams.get('date') ?? baseDay.date;
      const payload = {
        ...baseDay,
        date,
        lunar_day: Number(date.split('-')[2]),
        description: `Dream focus for ${date}`,
        recommendation: `Notes for ${date}`
      } satisfies LunarDayPayload;

      return new Response(JSON.stringify(payload), {
        headers: {'Content-Type': 'application/json'}
      });
    });

    render(
      <NextIntlProvider locale="en" messages={messages}>
        <LunarWidget initialData={baseDay} locale="en" />
      </NextIntlProvider>
    );

    await user.click(screen.getByRole('button', {name: messages.LunarWidget.showMonth}));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getAllByRole('row').length).toBeGreaterThan(1);
    });

    expect(screen.getByTestId(`row-${baseDay.date}`)).toHaveAttribute('aria-current', 'date');
  });
});
