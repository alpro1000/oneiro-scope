import {render, screen} from '@testing-library/react';
import ConfidenceBadge from '@/components/ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it('renders the score, source, and default label', () => {
    render(<ConfidenceBadge score={0.97} source="расчёт по эфемеридам" />);
    expect(screen.getByText('Достоверность')).toBeInTheDocument();
    expect(screen.getByText('0.97')).toBeInTheDocument();
    expect(screen.getByText('расчёт по эфемеридам')).toBeInTheDocument();
  });

  it('accepts a custom label', () => {
    render(<ConfidenceBadge score={0.6} source="tradition dictionary" label="Confidence" />);
    expect(screen.getByText('Confidence')).toBeInTheDocument();
  });

  it('clamps the meter fill to the 0..1 range', () => {
    const {container, rerender} = render(<ConfidenceBadge score={1.4} source="x" />);
    let fill = container.querySelector('span > span') as HTMLElement;
    expect(fill.style.width).toBe('100%');

    rerender(<ConfidenceBadge score={-0.2} source="x" />);
    fill = container.querySelector('span > span') as HTMLElement;
    expect(fill.style.width).toBe('0%');
  });
});
