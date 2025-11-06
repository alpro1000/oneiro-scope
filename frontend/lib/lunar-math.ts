export type PhaseKey =
  | 'New'
  | 'WaxingCrescent'
  | 'FirstQuarter'
  | 'WaxingGibbous'
  | 'Full'
  | 'WaningGibbous'
  | 'LastQuarter'
  | 'WaningCrescent';

const SYNODIC = 29.530588853;
const REF = new Date(Date.UTC(2000, 0, 6, 18, 14));
const PHASE_BREAKPOINTS: readonly number[] = [
  1.84566,
  5.53699,
  9.22831,
  12.91963,
  16.61096,
  20.30228,
  23.99361,
  27.68493
];

function positiveModulo(value: number, modulo: number): number {
  const remainder = value % modulo;
  return remainder < 0 ? remainder + modulo : remainder;
}

export function moonAge(moment: Date): number {
  const diffMs = moment.getTime() - REF.getTime();
  const days = diffMs / 86_400_000;
  return positiveModulo(days, SYNODIC);
}

export function lunarDayFromAge(age: number): number {
  return Math.max(1, Math.min(30, Math.floor(age) + 1));
}

export function phaseKeyFromAge(age: number): PhaseKey {
  if (age < PHASE_BREAKPOINTS[0] || age >= PHASE_BREAKPOINTS[PHASE_BREAKPOINTS.length - 1]) {
    return 'New';
  }
  if (age < PHASE_BREAKPOINTS[1]) {
    return 'WaxingCrescent';
  }
  if (age < PHASE_BREAKPOINTS[2]) {
    return 'FirstQuarter';
  }
  if (age < PHASE_BREAKPOINTS[3]) {
    return 'WaxingGibbous';
  }
  if (age < PHASE_BREAKPOINTS[4]) {
    return 'Full';
  }
  if (age < PHASE_BREAKPOINTS[5]) {
    return 'WaningGibbous';
  }
  if (age < PHASE_BREAKPOINTS[6]) {
    return 'LastQuarter';
  }
  if (age < PHASE_BREAKPOINTS[7]) {
    return 'WaningCrescent';
  }
  return 'New';
}

export function getLocalNoon(dateIso: string, tz: string): Date {
  const [year, month, day] = dateIso.split('-').map((part) => Number.parseInt(part, 10));
  if (Number.isNaN(year) || Number.isNaN(month) || Number.isNaN(day)) {
    throw new Error(`Invalid ISO date provided: ${dateIso}`);
  }

  const baseUtc = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  const parts = formatter.formatToParts(baseUtc);
  const lookup = Object.fromEntries(parts.map((part) => [part.type, part.value])) as Record<string, string>;
  const {year: yearPart, month: monthPart, day: dayPart, hour, minute, second} = lookup;

  if (!yearPart || !monthPart || !dayPart || !hour || !minute || !second) {
    throw new Error(`Unable to resolve timezone offset for ${dateIso} in ${tz}`);
  }

  const iso = `${yearPart}-${monthPart}-${dayPart}T${hour}:${minute}:${second}Z`;
  return new Date(iso);
}

export function computeLunarSnapshot(dateIso: string, tz: string) {
  const noonUtc = getLocalNoon(dateIso, tz);
  const age = moonAge(noonUtc);
  const lunarDay = lunarDayFromAge(age);
  const phaseKey = phaseKeyFromAge(age);
  return {age, lunarDay, phaseKey};
}
