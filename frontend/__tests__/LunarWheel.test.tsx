import {render} from '@testing-library/react';
import LunarWheel from '@/components/LunarWheel';

describe('LunarWheel', () => {
  it('renders an accessible SVG with the illumination percentage', () => {
    const {container} = render(<LunarWheel phaseKey="waxing_gibbous" illumination={0.68} />);
    expect(container.querySelector('svg[role="img"]')).toBeInTheDocument();
    expect(container.textContent).toContain('68%');
  });

  it('highlights the current phase with a larger glyph', () => {
    const {container} = render(<LunarWheel phaseKey="full_moon" illumination={1} />);
    const texts = Array.from(container.querySelectorAll('text'));
    const fullMoon = texts.find((el) => el.textContent === '🌕');
    expect(fullMoon?.getAttribute('font-size')).toBe('22');
  });

  it('omits the percentage label when illumination is not provided', () => {
    const {container} = render(<LunarWheel phaseKey="new_moon" />);
    expect(container.textContent).not.toMatch(/%/);
  });

  it('does not crash and highlights nothing for an unknown phase key', () => {
    const {container} = render(<LunarWheel phaseKey="unknown_phase" illumination={0.5} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});
