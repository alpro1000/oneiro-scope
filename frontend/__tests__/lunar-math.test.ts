import {
  computeLunarSnapshot,
  getLocalNoon,
  lunarDayFromAge,
  moonAge,
  phaseKeyFromAge
} from '@/lib/lunar-math';

describe('lunar math helpers', () => {
  it('normalises the moon age at the reference new moon', () => {
    const reference = new Date(Date.UTC(2000, 0, 6, 18, 14));
    expect(moonAge(reference)).toBeCloseTo(0, 6);
  });

  it('derives the lunar day number from the fractional age', () => {
    expect(lunarDayFromAge(0.2)).toBe(1);
    expect(lunarDayFromAge(14.7)).toBe(15);
    expect(lunarDayFromAge(29.2)).toBe(30);
  });

  it('maps lunar age to the correct phase buckets', () => {
    expect(phaseKeyFromAge(0.5)).toBe('New');
    expect(phaseKeyFromAge(4.2)).toBe('WaxingCrescent');
    expect(phaseKeyFromAge(8.1)).toBe('FirstQuarter');
    expect(phaseKeyFromAge(13.5)).toBe('WaxingGibbous');
    expect(phaseKeyFromAge(17.2)).toBe('Full');
    expect(phaseKeyFromAge(22.1)).toBe('LastQuarter');
    expect(phaseKeyFromAge(27.2)).toBe('WaningCrescent');
  });

  it('calculates UTC noon for a given locale-aware date', () => {
    const noon = getLocalNoon('2000-01-14', 'Europe/Prague');
    expect(noon.toISOString()).toBe('2000-01-14T11:00:00.000Z');
  });

  it('produces accurate lunar snapshots for historic dates', () => {
    const utcSnapshot = computeLunarSnapshot('2000-01-21', 'UTC');
    expect(utcSnapshot.lunarDay).toBe(15);
    expect(utcSnapshot.phaseKey).toBe('Full');
    expect(utcSnapshot.age).toBeCloseTo(14.7402777, 4);

    const pragueSnapshot = computeLunarSnapshot('2000-01-14', 'Europe/Prague');
    expect(pragueSnapshot.lunarDay).toBe(8);
    expect(pragueSnapshot.phaseKey).toBe('FirstQuarter');
    expect(pragueSnapshot.age).toBeCloseTo(7.6986111, 4);
  });
});
