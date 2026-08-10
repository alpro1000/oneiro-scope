import type { ChartCore } from '@oneiroscope/chart-kit';

/**
 * Sample chart — Greenwich Observatory, noon on 2000-01-01.
 *
 * Screens need something on them before the user has entered anything, or the
 * wheel and the map are an empty frame that teaches nothing. What they must
 * NOT show is a person: this file previously shipped the owner's real birth
 * date, time and city to every visitor, and — worse for the reader — a chart
 * that looks like theirs but is somebody else's is not a sample, it is a
 * wrong answer. Hence a place and a moment instead: the reference meridian,
 * where longitude is defined, at the top of the millennium.
 *
 * Real numbers from the server's own builder
 * (`backend/services/astrology/chart_core.py::build_chart_core`), so every
 * angle, cusp, aspect and astrocartography line `@oneiroscope/chart-kit`
 * derives from it is correct — the sample behaves exactly like live data, and
 * the screens are exercised rather than faked. Replaced wholesale by
 * `POST /api/v1/chart` as soon as the user submits their own details.
 *
 * `SAMPLE_LABEL` is what the UI must show while this is on screen. Every
 * screen that seeds itself with `SAMPLE_CORE` is responsible for saying so —
 * an unlabelled sample is indistinguishable from a computed result.
 *
 * Shared by the natal and astrocartography screens so the two never drift.
 */
export const SAMPLE_CORE: ChartCore = {
  version: '1', jd_ut: 2451545.0, gmst: 280.4571, obliquity: 23.43768,
  birth: {
    lat: 51.4779, lon: -0.0015, tz_used: 'Europe/London', utc_offset_used: '+00:00',
    tz_source: 'explicit', local_clock: '2000-01-01T12:00:00',
    utc: '2000-01-01T12:00:00+00:00', place_label: 'Greenwich', time_known: true,
  },
  bodies: {
    Sun: { ecl_lon: 280.3689, ecl_lat: 0.0002, ra: 281.2784, dec: -23.0324, speed_lon: 1.0194, retrograde: false },
    Moon: { ecl_lon: 223.3238, ecl_lat: 5.1707, ra: 222.4522, dec: -10.9006, speed_lon: 12.0213, retrograde: false },
    Mercury: { ecl_lon: 271.8893, ecl_lat: -0.9948, ra: 272.0746, dec: -24.4189, speed_lon: 1.5563, retrograde: false },
    Venus: { ecl_lon: 241.5658, ecl_lat: 2.0663, ra: 239.8928, dec: -18.4489, speed_lon: 1.209, retrograde: false },
    Mars: { ecl_lon: 327.9633, ecl_lat: -1.0678, ra: 330.5168, dec: -13.1825, speed_lon: 0.7757, retrograde: false },
    Jupiter: { ecl_lon: 25.2531, ecl_lat: -1.2622, ra: 23.8679, dec: 8.5943, speed_lon: 0.0408, retrograde: false },
    Saturn: { ecl_lon: 40.3957, ecl_lat: -2.4449, ra: 38.7654, dec: 12.6148, speed_lon: -0.0199, retrograde: true },
    Uranus: { ecl_lon: 314.8092, ecl_lat: -0.6583, ra: 317.4748, dec: -17.0203, speed_lon: 0.0503, retrograde: false },
    Neptune: { ecl_lon: 303.193, ecl_lat: 0.235, ra: 305.4328, dec: -19.2132, speed_lon: 0.0356, retrograde: false },
    Pluto: { ecl_lon: 251.4548, ecl_lat: 10.8552, ra: 251.4192, dec: -11.3943, speed_lon: 0.0352, retrograde: false },
    TrueNode: { ecl_lon: 123.954, ecl_lat: 0.0, ra: 126.2747, dec: 19.2645, speed_lon: -0.0547, retrograde: true },
    Chiron: { ecl_lon: 251.6176, ecl_lat: 4.0717, ra: 250.6696, dec: -18.141, speed_lon: 0.1143, retrograde: false },
  },
  node_type: 'true', house_system: 'placidus',
};

/** Banner text for a screen still showing `SAMPLE_CORE`. */
export const SAMPLE_LABEL: Record<'ru' | 'en', string> = {
  ru: 'Образец: Гринвич, 1 января 2000, 12:00. Введите свои данные ниже — '
    + 'карта пересчитается.',
  en: 'Sample: Greenwich, 1 January 2000, 12:00. Enter your own details below '
    + '— the chart will be recomputed.',
};

/** True while the screen is still showing the sample rather than a result. */
export const isSample = (core: ChartCore): boolean =>
  core.jd_ut === SAMPLE_CORE.jd_ut;
