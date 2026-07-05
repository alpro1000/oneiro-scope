/**
 * Live capture gates for the face scanner — pure math, no DOM.
 *
 * Mirrors the backend gates (backend/services/physiognomy/geometry.py)
 * but STRICTER, so every auto-captured frame is guaranteed to pass the
 * server: yaw 0.15 vs server 0.20, mouth 0.05 vs server 0.06.
 * Landmark indices follow the MediaPipe FaceMesh 468-point topology.
 */

export type Point = { x: number; y: number };

// FaceMesh canonical indices (same as backend geometry.py).
export const EYE_L_OUT = 33;
export const EYE_L_IN = 133;
export const EYE_R_IN = 362;
export const EYE_R_OUT = 263;
export const LIP_TOP = 13;
export const LIP_BOTTOM = 14;
export const MOUTH_L = 61;
export const MOUTH_R = 291;
export const FOREHEAD_TOP = 10;
export const CHIN = 152;
export const CHEEK_L = 234;
export const CHEEK_R = 454;

export const MAX_EYE_ASYMMETRY = 0.15; // server rejects at 0.20
export const MAX_MOUTH_OPENNESS = 0.05; // server distrusts lips at 0.06
export const MIN_FACE_SHARE = 0.25; // face height as share of frame height
export const MAX_BRIGHTNESS_RATIO = 1.4; // left/right cheek luminance

const d = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

/** Head rotation proxy: unequal visible eye widths. */
export function eyeAsymmetry(lms: Point[]): number {
  const eyeL = d(lms[EYE_L_OUT], lms[EYE_L_IN]);
  const eyeR = d(lms[EYE_R_IN], lms[EYE_R_OUT]);
  const max = Math.max(eyeL, eyeR);
  return max > 0 ? Math.abs(eyeL - eyeR) / max : 1;
}

/** Inner-lip gap over mouth width — expression, not anatomy. */
export function mouthOpenness(lms: Point[]): number {
  const mouthW = d(lms[MOUTH_L], lms[MOUTH_R]);
  return mouthW > 0 ? d(lms[LIP_TOP], lms[LIP_BOTTOM]) / mouthW : 1;
}

/** Face height as a share of the frame (landmarks normalized 0..1). */
export function faceShare(lms: Point[]): number {
  return Math.abs(lms[CHIN].y - lms[FOREHEAD_TOP].y);
}

/** Uneven side lighting kills texture AND shifts landmark contrast. */
export function brightnessOk(left: number, right: number): boolean {
  if (left <= 0 || right <= 0) return false;
  const ratio = Math.max(left, right) / Math.min(left, right);
  return ratio <= MAX_BRIGHTNESS_RATIO;
}

export interface GateState {
  yawOk: boolean;
  mouthOk: boolean;
  sizeOk: boolean;
}

/** Evaluate the geometry gates on normalized landmarks. */
export function evaluateGates(lms: Point[]): GateState {
  return {
    yawOk: eyeAsymmetry(lms) <= MAX_EYE_ASYMMETRY,
    mouthOk: mouthOpenness(lms) <= MAX_MOUTH_OPENNESS,
    sizeOk: faceShare(lms) >= MIN_FACE_SHARE,
  };
}

/** Normalized landmarks → pixel [[x, y], ...] for the backend. */
export function toPixelFrame(
  lms: Point[], width: number, height: number
): number[][] {
  return lms.map((p) => [p.x * width, p.y * height]);
}
