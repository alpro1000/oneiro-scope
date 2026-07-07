import {render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {NextIntlClientProvider} from 'next-intl';
import ThemeToggle from '@/components/ThemeToggle';
import messages from '../messages/en.json';

function renderToggle() {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ThemeToggle />
    </NextIntlClientProvider>
  );
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('reflects whatever ThemeInit already set on <html> (dark)', async () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    renderToggle();
    expect(await screen.findByRole('button', {name: messages.Header.themeLight})).toBeInTheDocument();
  });

  it('reflects light theme when set on <html>', async () => {
    document.documentElement.setAttribute('data-theme', 'light');
    renderToggle();
    expect(await screen.findByRole('button', {name: messages.Header.themeDark})).toBeInTheDocument();
  });

  it('toggles the theme and persists it to localStorage', async () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    renderToggle();
    const user = userEvent.setup();

    const button = await screen.findByRole('button', {name: messages.Header.themeLight});
    await user.click(button);

    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem('oneiro-theme')).toBe('light');
    expect(await screen.findByRole('button', {name: messages.Header.themeDark})).toBeInTheDocument();
  });
});
