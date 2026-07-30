import type { ChartCore } from '@oneiroscope/chart-kit';

/**
 * Demo chart — Swiss Ephemeris for 1977-07-01 19:30 UTC (Запорожье).
 *
 * Real numbers from the server's own builder (`scripts/generate_chart_golden.py`),
 * used to seed screens before a fetch so the wheel/map are never empty. Replaced
 * wholesale by `POST /api/v1/chart`. The client never computes an ephemeris —
 * every angle, cusp, aspect and astrocartography line is DERIVED from this core
 * by `@oneiroscope/chart-kit`, which is exactly why one core works offline.
 *
 * Shared by the natal and astrocartography screens so the two never drift.
 */
export const DEMO_CORE: ChartCore = {
  version: '1', jd_ut: 2443326.3125, gmst: 212.2347, obliquity: 23.43962,
  birth: {
    lat: 47.8388, lon: 35.1396, tz_used: 'Europe/Kyiv', utc_offset_used: '+03:00',
    tz_source: 'coordinates', local_clock: '1977-07-01T22:30:00',
    utc: '1977-07-01T19:30:00+00:00', place_label: 'Запорожье', time_known: true,
  },
  bodies: {
    Sun: { ecl_lon: 99.8251, ecl_lat: 0.0, ra: 100.6892, dec: 23.0758, speed_lon: 0.9531, retrograde: false },
    Moon: { ecl_lon: 289.2449, ecl_lat: 5.0182, ra: 290.0909, dec: -17.0892, speed_lon: 14.9173, retrograde: false },
    Mercury: { ecl_lon: 102.0171, ecl_lat: 1.457, ra: 103.206, dec: 24.3474, speed_lon: 2.1629, retrograde: false },
    Venus: { ecl_lon: 54.9195, ecl_lat: -2.8885, ra: 53.294, dec: 16.1931, speed_lon: 1.0446, retrograde: false },
    Mars: { ecl_lon: 48.8009, ecl_lat: -0.8224, ra: 46.58, dec: 16.6247, speed_lon: 0.7176, retrograde: false },
    Jupiter: { ecl_lon: 79.947, ecl_lat: -0.4507, ra: 79.1006, dec: 22.6094, speed_lon: 0.2246, retrograde: false },
    Saturn: { ecl_lon: 135.1816, ecl_lat: 0.9798, ra: 137.9467, dec: 17.2193, speed_lon: 0.1124, retrograde: false },
    Uranus: { ecl_lon: 217.7776, ecl_lat: 0.437, ra: 215.5623, dec: -13.6905, speed_lon: -0.0123, retrograde: true },
    Neptune: { ecl_lon: 254.0923, ecl_lat: 1.5263, ra: 252.9362, dec: -20.9759, speed_lon: -0.0236, retrograde: true },
    Pluto: { ecl_lon: 191.4284, ecl_lat: 17.0623, ra: 197.2248, dec: 11.1776, speed_lon: 0.0058, retrograde: false },
    TrueNode: { ecl_lon: 200.8278, ecl_lat: 0.0, ra: 199.2404, dec: -8.131, speed_lon: -0.179, retrograde: true },
    Chiron: { ecl_lon: 35.121, ecl_lat: -0.3641, ra: 32.9597, dec: 12.886, speed_lon: 0.0331, retrograde: false },
  },
  node_type: 'true', house_system: 'placidus',
};
