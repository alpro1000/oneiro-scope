import {render, screen} from '@testing-library/react';
import FindingCard from '@/components/FindingCard';

describe('FindingCard', () => {
  const base = {
    title: 'Широко расставленные глаза',
    seenText: '1.25 (нейтраль 1.00, порог ≥1.12) · подтверждено 11/11 кадров',
    traditionQuote: 'широта восприятия, неторопливость суждений',
    traditionSource: 'Joey Yap, 2006',
    humanText: 'Сначала охватывает всю картину, потом замечает частности.',
    plusText: 'взвешенность',
    minusText: 'мелкие детали ускользают',
  };

  it('renders all four zones: measurement, tradition, human, balance', () => {
    render(<FindingCard {...base} />);

    expect(screen.getByText(base.title)).toBeInTheDocument();
    expect(screen.getByText('Система увидела')).toBeInTheDocument();
    expect(screen.getByText(base.seenText)).toBeInTheDocument();
    expect(screen.getByText(base.traditionQuote)).toBeInTheDocument();
    expect(screen.getByText(base.traditionSource)).toBeInTheDocument();
    expect(screen.getByText(base.humanText)).toBeInTheDocument();
    expect(screen.getByText(base.plusText)).toBeInTheDocument();
    expect(screen.getByText(base.minusText)).toBeInTheDocument();
  });

  it('omits the life-context banner when none is given', () => {
    render(<FindingCard {...base} />);
    expect(screen.queryByText(/✅/)).not.toBeInTheDocument();
  });

  it('shows the life-context override above the plus/minus split when given', () => {
    const note = 'Разговорчив — словарное «скупость на слова» опровергнуто.';
    render(<FindingCard {...base} lifeContext={note} />);
    expect(screen.getByText(`✅ ${note}`)).toBeInTheDocument();
  });

  it('accepts custom labels for the seen/plus/minus zones', () => {
    render(
      <FindingCard
        {...base}
        seenLabel="Custom seen"
        plusLabel="Custom plus"
        minusLabel="Custom minus"
      />
    );
    expect(screen.getByText('Custom seen')).toBeInTheDocument();
    expect(screen.getByText('Custom plus')).toBeInTheDocument();
    expect(screen.getByText('Custom minus')).toBeInTheDocument();
  });
});
