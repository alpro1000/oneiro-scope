import {render} from '@testing-library/react';
import NatalWheel from '@/components/NatalWheel';
import type {Aspect, PlanetPosition} from '@/lib/astrology-client';

const planets: PlanetPosition[] = [
  {planet: 'sun', sign: 'virgo', degree: 164, sign_degree: 14, retrograde: false},
  {planet: 'moon', sign: 'cancer', degree: 87, sign_degree: 27, retrograde: false},
];

const aspects: Aspect[] = [
  {planet1: 'sun', planet2: 'moon', aspect_type: 'trine', orb: 2, applying: true},
];

describe('NatalWheel', () => {
  it('renders an accessible SVG with a planet glyph per planet', () => {
    const {container} = render(<NatalWheel planets={planets} aspects={aspects} />);
    const svg = container.querySelector('svg[role="img"]');
    expect(svg).toBeInTheDocument();
    expect(container.textContent).toContain('☉');
    expect(container.textContent).toContain('☽');
  });

  it('draws an aspect line only when both planets are present', () => {
    const {container} = render(<NatalWheel planets={planets} aspects={aspects} />);
    expect(container.querySelectorAll('line').length).toBeGreaterThan(0);
  });

  it('skips aspect lines for planets missing from the position list', () => {
    const {container: withMissing} = render(
      <NatalWheel planets={[planets[0]]} aspects={aspects} />
    );
    const {container: withBoth} = render(<NatalWheel planets={planets} aspects={aspects} />);
    expect(withMissing.querySelectorAll('line').length).toBeLessThan(
      withBoth.querySelectorAll('line').length
    );
  });

  it('draws the ASC line and label only when ascendantSign is given', () => {
    const {container: without} = render(<NatalWheel planets={planets} aspects={[]} />);
    expect(without.textContent).not.toContain('ASC');

    const {container: withAsc} = render(
      <NatalWheel planets={planets} aspects={[]} ascendantSign="scorpio" />
    );
    expect(withAsc.textContent).toContain('ASC');
  });

  it('marks retrograde planets', () => {
    const retro: PlanetPosition[] = [
      {planet: 'mercury', sign: 'libra', degree: 190, sign_degree: 10, retrograde: true},
    ];
    const {container} = render(<NatalWheel planets={retro} aspects={[]} />);
    expect(container.textContent).toContain('℞');
  });
});
