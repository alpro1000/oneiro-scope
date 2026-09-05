/**
 * Equirectangular projection and latitude clipping for the astrocartography
 * map. Pure functions, no DOM — `acg-map.ts` mounts a view on import, so the
 * geometry that needs testing lives here instead.
 */

// Latitude window of the reference basemap: past these the equirectangular
// projection stretches into uselessness.
export const LAT_TOP = 78;
export const LAT_BOTTOM = -58;

export const W = 1000;
export const H = Math.round((W * (LAT_TOP - LAT_BOTTOM)) / 360);
export const px = (lon: number) => ((lon + 180) / 360) * W;
export const py = (lat: number) => ((LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM)) * H;
export const n2 = (v: number) => Math.round(v * 100) / 100;

/**
 * A polyline, clipped to the map's latitude window and split where it wraps
 * the antimeridian.
 *
 * Without the split a curve leaving at +180° draws a straight line all the way
 * back across the map — a line through places the planet is nowhere near.
 *
 * The clip TRUNCATES a segment at the window edge; it used to DROP any point
 * outside it, and that silently erased every meridian on the map. The server
 * emits MC and IC as two-point LineStrings spanning latitude -58…80 — two
 * degrees past this window's 78 — so the northern endpoint was dropped, one
 * point survived, `run.length > 1` rejected it, and all twenty MC/IC lines
 * vanished. The map still drew the Asc/Desc curves, the legend still listed
 * every planet (it is built from the features, not from what was drawn), and
 * the footer still counted 46 lines: a half-drawn map that looked whole.
 * Truncating instead of dropping is also simply more correct for the curves,
 * whose old rendering stopped a whole sample short of the edge.
 */
export function pathFor(coords: number[][]): string[] {
  const runs: string[][] = [];
  let run: string[] = [];
  let prev: [number, number] | null = null;

  const inside = (lat: number) => lat <= LAT_TOP && lat >= LAT_BOTTOM;
  const pt = (lon: number, lat: number) => `${n2(px(lon))},${n2(py(lat))}`;
  // Where a segment crosses the window edge. Latitude is the parameter, so a
  // meridian (constant longitude) lands exactly on its own line.
  const crossing = (
    a: [number, number], b: [number, number], edge: number,
  ): [number, number] => {
    const span = b[1] - a[1];
    const f = span === 0 ? 0 : (edge - a[1]) / span;
    return [a[0] + (b[0] - a[0]) * f, edge];
  };

  for (const [lon, lat] of coords) {
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    const here: [number, number] = [lon, lat];

    if (prev !== null && Math.abs(lon - prev[0]) > 180) {
      if (run.length > 1) runs.push(run);
      run = [];
      prev = null;
    }

    if (inside(lat)) {
      // Entering the window: start at the edge, not at this sample.
      if (prev !== null && !inside(prev[1])) {
        const edge = prev[1] > LAT_TOP ? LAT_TOP : LAT_BOTTOM;
        run.push(pt(...crossing(prev, here, edge)));
      }
      run.push(pt(lon, lat));
    } else if (prev !== null && inside(prev[1])) {
      // Leaving the window: finish at the edge, then break the run.
      const edge = lat > LAT_TOP ? LAT_TOP : LAT_BOTTOM;
      run.push(pt(...crossing(prev, here, edge)));
      if (run.length > 1) runs.push(run);
      run = [];
    } else if (prev !== null && !inside(prev[1]) && (prev[1] > LAT_TOP) !== (lat > LAT_TOP)) {
      // Both ends outside, on OPPOSITE sides: the segment crosses the whole
      // window. A meridian from -58 to 80 with a taller window is this case.
      run.push(pt(...crossing(prev, here, prev[1] > LAT_TOP ? LAT_TOP : LAT_BOTTOM)));
      run.push(pt(...crossing(prev, here, lat > LAT_TOP ? LAT_TOP : LAT_BOTTOM)));
      runs.push(run);
      run = [];
    }
    prev = here;
  }
  if (run.length > 1) runs.push(run);
  return runs.map((r) => r.join(' '));
}
