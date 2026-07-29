/**
 * chart-kit — everything derivable from a `chart_core`, computed locally.
 *
 * The server sends one ~1.7 KB payload per chart. From it this package
 * derives angles and house cusps for any point on Earth, aspects,
 * dignities, astrocartography lines and angle contacts — with no
 * network, no ephemeris and no further cost. That is why the paywall
 * sits on the payload rather than on features, and why the app works
 * offline once a chart is cached.
 *
 * Every export is a pure function of its arguments. The golden tests
 * check the whole surface against the server on 20 charts (polar,
 * equatorial, several epochs, midnight boundaries) to 0.01°; a larger
 * divergence fails CI, because two implementations of one formula
 * always drift and the client must never show what the server would not.
 */

export * from './types';
export {
  angles,
  houseCusps,
  houses,
  houseOf,
  norm360,
  ramc,
  resolveSystemFor,
  sep180,
} from './angles';
export {
  ASPECTS,
  SIGNS,
  aspects,
  contacts,
  degreeInSign,
  dignities,
  signOf,
} from './aspects';
export { acgLines, mcLongitude } from './acg';
export type { AcgLine, LineKind } from './acg';
