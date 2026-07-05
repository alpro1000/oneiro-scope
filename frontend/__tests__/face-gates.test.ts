/**
 * Face scanner gates — pure math mirror of the backend gates
 * (stricter thresholds, so captured frames always pass the server).
 */

import {
  brightnessOk,
  CHIN,
  evaluateGates,
  eyeAsymmetry,
  EYE_L_IN,
  EYE_L_OUT,
  EYE_R_IN,
  EYE_R_OUT,
  FOREHEAD_TOP,
  LIP_BOTTOM,
  LIP_TOP,
  MOUTH_L,
  MOUTH_R,
  mouthOpenness,
  toPixelFrame,
  type Point,
} from '../lib/face-gates';

/** Normalized synthetic face mirroring the backend test fixture. */
function syntheticFace(): Point[] {
  const pts: Point[] = Array.from({ length: 468 }, () => ({
    x: 0.5,
    y: 0.5,
  }));
  pts[FOREHEAD_TOP] = { x: 0.5, y: 0.1 };
  pts[CHIN] = { x: 0.5, y: 0.9 };
  pts[EYE_L_OUT] = { x: 0.3, y: 0.4 };
  pts[EYE_L_IN] = { x: 0.42, y: 0.4 };
  pts[EYE_R_IN] = { x: 0.58, y: 0.4 };
  pts[EYE_R_OUT] = { x: 0.7, y: 0.4 };
  pts[MOUTH_L] = { x: 0.42, y: 0.75 };
  pts[MOUTH_R] = { x: 0.58, y: 0.75 };
  pts[LIP_TOP] = { x: 0.5, y: 0.748 };
  pts[LIP_BOTTOM] = { x: 0.5, y: 0.752 };
  return pts;
}

describe('face-gates', () => {
  it('passes all geometry gates on a frontal closed-mouth face', () => {
    const g = evaluateGates(syntheticFace());
    expect(g).toEqual({ yawOk: true, mouthOk: true, sizeOk: true });
  });

  it('fails the yaw gate when one eye is foreshortened', () => {
    const pts = syntheticFace();
    pts[EYE_R_OUT] = { x: 0.64, y: 0.4 }; // eye width halved
    expect(eyeAsymmetry(pts)).toBeGreaterThan(0.15);
    expect(evaluateGates(pts).yawOk).toBe(false);
  });

  it('fails the mouth gate when the mouth is open', () => {
    const pts = syntheticFace();
    pts[LIP_BOTTOM] = { x: 0.5, y: 0.79 }; // wide gap
    expect(mouthOpenness(pts)).toBeGreaterThan(0.05);
    expect(evaluateGates(pts).mouthOk).toBe(false);
  });

  it('fails the size gate when the face is too small in frame', () => {
    const pts = syntheticFace().map((p) => ({
      x: 0.5 + (p.x - 0.5) * 0.2,
      y: 0.5 + (p.y - 0.5) * 0.2,
    }));
    expect(evaluateGates(pts).sizeOk).toBe(false);
  });

  it('brightness gate rejects one-sided lighting', () => {
    expect(brightnessOk(120, 110)).toBe(true);
    expect(brightnessOk(200, 90)).toBe(false);
    expect(brightnessOk(0, 100)).toBe(false);
  });

  it('converts normalized landmarks to pixel frames for the API', () => {
    const frame = toPixelFrame(syntheticFace(), 1000, 500);
    expect(frame).toHaveLength(468);
    expect(frame[FOREHEAD_TOP]).toEqual([500, 50]);
  });
});
