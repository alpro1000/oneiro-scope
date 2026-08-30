/**
 * The astrocartography map lost every meridian, and nothing said so.
 *
 * `astrocartography_lines` emits MC and IC as two-point LineStrings spanning
 * latitude -58…80. `pathFor` clipped by DROPPING any point outside its -58…78
 * window, so the northern endpoint went, a single point survived, and the
 * `run.length > 1` guard rejected it. Twenty of forty-six features never
 * reached the SVG. Everything around them kept claiming they had: the legend
 * lists planets found in the FEATURES, not in what was drawn, and the footer
 * counts `features.length`. So the map read as complete while missing the
 * meridians — the lines a reader means by "my Sun line".
 *
 * These tests are about geometry the view must not lose, which is why they
 * assert on point counts and coordinates rather than on markup.
 */
import { describe, expect, it } from 'vitest';
import { LAT_BOTTOM, LAT_TOP, pathFor, px } from '../src/acg-geometry';

/** Every "x,y" pair of a run, as numbers. */
const points = (run: string) => run.split(' ').map((p) => p.split(',').map(Number));

describe('pathFor', () => {
  it('draws a meridian that overshoots the window at BOTH ends', () => {
    // The exact shape the server sends for MC/IC.
    const runs = pathFor([[21.57, LAT_BOTTOM], [21.57, 80]]);
    expect(runs).toHaveLength(1);

    const pts = points(runs[0]);
    expect(pts).toHaveLength(2);
    // A meridian is vertical: clipping must not move it sideways.
    expect(pts[0][0]).toBeCloseTo(pts[1][0], 6);
    // …and it must span the full drawable height, not stop short.
    const ys = pts.map((p) => p[1]).sort((a, b) => a - b);
    expect(ys[0]).toBeCloseTo(0, 6);
  });

  it('draws a meridian that crosses the window with both ends outside', () => {
    const runs = pathFor([[10, -90], [10, 90]]);
    expect(runs).toHaveLength(1);
    const pts = points(runs[0]);
    expect(pts).toHaveLength(2);
    expect(pts[0][0]).toBeCloseTo(pts[1][0], 6);
  });

  it('truncates a curve at the edge instead of stopping a sample short', () => {
    // Enters the window between the first and second sample: the segment runs
    // from lat 85 to lat 70, so it meets LAT_TOP (78) at 7/15 of the way,
    // i.e. longitude 4.667.
    const runs = pathFor([[0, 85], [10, 70], [20, 60]]);
    expect(runs).toHaveLength(1);
    const pts = points(runs[0]);
    // 3 points: the interpolated edge crossing plus the two inside samples.
    expect(pts).toHaveLength(3);
    expect(pts[0][0]).toBeCloseTo(px(10 * (7 / 15)), 1);
    // On the edge means y = 0 in the projection.
    expect(pts[0][1]).toBeCloseTo(0, 6);
    // …and strictly between the two samples it interpolates.
    expect(pts[0][0]).toBeGreaterThan(px(0));
    expect(pts[0][0]).toBeLessThan(px(10));
  });

  it('still splits at the antimeridian rather than drawing across the map', () => {
    const runs = pathFor([[170, 10], [179, 12], [-179, 13], [-170, 14]]);
    expect(runs).toHaveLength(2);
  });

  it('drops a segment that never enters the window', () => {
    expect(pathFor([[0, 85], [10, 88]])).toHaveLength(0);
    expect(pathFor([[0, -80], [10, -85]])).toHaveLength(0);
  });

  it('ignores non-finite coordinates without breaking the run', () => {
    const runs = pathFor([[0, 10], [Number.NaN, 20], [10, 30]]);
    expect(runs).toHaveLength(1);
    expect(points(runs[0])).toHaveLength(2);
  });

  it('keeps a line that sits exactly on an edge', () => {
    expect(pathFor([[5, LAT_TOP], [6, LAT_TOP - 1]])).toHaveLength(1);
    expect(pathFor([[5, LAT_BOTTOM], [6, LAT_BOTTOM + 1]])).toHaveLength(1);
  });
});
