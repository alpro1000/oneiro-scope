'use client';

/**
 * Guided face scanner — the "встречный сканер" of the physiognomy
 * pipeline (docs/specs/photo-max-extraction, Gate 4).
 *
 * Runs MediaPipe FaceLandmarker in the browser, shows live gate
 * feedback (head straight / mouth closed / come closer / even light),
 * auto-captures frames only while ALL gates pass, then sends the
 * landmark coordinates (never the pixels) to /analyze-archive and
 * renders the aggregated profile.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  brightnessOk,
  CHEEK_L,
  CHEEK_R,
  evaluateGates,
  toPixelFrame,
  type GateState,
  type Point,
} from '../lib/face-gates';
import {
  analyzeFaceArchive,
  type ArchiveResponse,
} from '../lib/physiognomy-client';

const TARGET_FRAMES = 5;
const CAPTURE_SPACING_MS = 600; // spread captures over distinct moments
// The wasm runtime and the model are served from THIS origin by default
// (vendored under public/vendor/mediapipe — see scripts/vendor-mediapipe.mjs).
// Loading them from a third-party CDN at runtime was the cause of the "Load
// failed" screen when that host was blocked for the visitor. Both stay
// overridable by env if a CDN is ever preferred.
const WASM_BASE =
  process.env.NEXT_PUBLIC_FACE_WASM_URL || '/vendor/mediapipe/wasm';
const MODEL_URL =
  process.env.NEXT_PUBLIC_FACE_MODEL_URL ||
  '/vendor/mediapipe/face_landmarker.task';

type Phase =
  | 'idle'
  | 'loading'
  | 'scanning'
  | 'analyzing'
  | 'done'
  | 'error';

interface LiveGates extends GateState {
  lightOk: boolean;
  faceFound: boolean;
}

const NO_GATES: LiveGates = {
  faceFound: false,
  yawOk: false,
  mouthOk: false,
  sizeOk: false,
  lightOk: false,
};

/** Mean luminance of a small patch around a landmark (pixel coords). */
function patchLuma(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number
): number {
  const x = Math.max(0, Math.round(cx - r));
  const y = Math.max(0, Math.round(cy - r));
  const size = Math.max(2, Math.round(2 * r));
  const data = ctx.getImageData(x, y, size, size).data;
  let sum = 0;
  for (let i = 0; i < data.length; i += 4) {
    sum += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  }
  return sum / (data.length / 4);
}

export default function FaceScanner({ locale }: { locale: string }) {
  const t = useTranslations('FacePage');
  const ru = locale === 'ru';
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const landmarkerRef = useRef<{
    detectForVideo: (
      v: HTMLVideoElement,
      ts: number
    ) => { faceLandmarks: Point[][] };
    close: () => void;
  } | null>(null);
  const rafRef = useRef(0);
  const framesRef = useRef<number[][][]>([]);
  const lastCaptureRef = useRef(0);

  const [phase, setPhase] = useState<Phase>('idle');
  const [gates, setGates] = useState<LiveGates>(NO_GATES);
  const [captured, setCaptured] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ArchiveResponse | null>(null);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    const video = videoRef.current;
    if (video?.srcObject) {
      (video.srcObject as MediaStream).getTracks().forEach((tr) => tr.stop());
      video.srcObject = null;
    }
    landmarkerRef.current?.close();
    landmarkerRef.current = null;
  }, []);

  useEffect(() => stop, [stop]);

  const analyze = useCallback(
    async (frames: number[][][]) => {
      stop();
      setPhase('analyzing');
      try {
        setResult(await analyzeFaceArchive(frames, locale));
        setPhase('done');
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase('error');
      }
    },
    [locale, stop]
  );

  const loop = useCallback(() => {
    const video = videoRef.current;
    const landmarker = landmarkerRef.current;
    if (!video || !landmarker || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(loop);
      return;
    }
    const res = landmarker.detectForVideo(video, performance.now());
    const lms = res.faceLandmarks?.[0];
    if (!lms) {
      setGates(NO_GATES);
      rafRef.current = requestAnimationFrame(loop);
      return;
    }

    const g = evaluateGates(lms);
    // Lighting gate needs pixels: sample cheek patches off a canvas.
    let lightOk = false;
    const canvas = canvasRef.current;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (canvas && w && h) {
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (ctx) {
        ctx.drawImage(video, 0, 0);
        const r = Math.max(4, 0.02 * w);
        lightOk = brightnessOk(
          patchLuma(ctx, lms[CHEEK_L].x * w, lms[CHEEK_L].y * h, r),
          patchLuma(ctx, lms[CHEEK_R].x * w, lms[CHEEK_R].y * h, r)
        );
      }
    }
    setGates({ faceFound: true, ...g, lightOk });

    const allOk = g.yawOk && g.mouthOk && g.sizeOk && lightOk;
    const now = performance.now();
    if (allOk && now - lastCaptureRef.current >= CAPTURE_SPACING_MS) {
      lastCaptureRef.current = now;
      framesRef.current.push(toPixelFrame(lms, w, h));
      setCaptured(framesRef.current.length);
      if (framesRef.current.length >= TARGET_FRAMES) {
        void analyze(framesRef.current);
        return;
      }
    }
    rafRef.current = requestAnimationFrame(loop);
  }, [analyze]);

  const start = useCallback(async () => {
    setError(null);
    setResult(null);
    setCaptured(0);
    framesRef.current = [];
    lastCaptureRef.current = 0;
    setPhase('loading');
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(t('errorNoCamera'));
      }
      // Camera first, so a permission/HTTPS denial is reported as a camera
      // error — distinct from a model-load failure below.
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 } },
          audio: false,
        });
      } catch {
        throw new Error(t('errorNoCamera'));
      }
      // Model + wasm runtime (same-origin by default). A failure here is the
      // model/runtime load — surfaced as a clear message, never the browser's
      // raw "Load failed" fetch error.
      try {
        const { FaceLandmarker, FilesetResolver } = await import(
          '@mediapipe/tasks-vision'
        );
        const fileset = await FilesetResolver.forVisionTasks(WASM_BASE);
        landmarkerRef.current = await FaceLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: MODEL_URL },
          runningMode: 'VIDEO',
          numFaces: 1,
        });
      } catch {
        stream.getTracks().forEach((tr) => tr.stop());
        throw new Error(t('errorModelLoad'));
      }
      const video = videoRef.current;
      if (!video) throw new Error('video element missing');
      video.srcObject = stream;
      await video.play();
      setPhase('scanning');
      rafRef.current = requestAnimationFrame(loop);
    } catch (e) {
      stop();
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  }, [loop, stop, t]);

  const gateItems: { key: keyof LiveGates; label: string }[] = [
    { key: 'faceFound', label: t('gateFace') },
    { key: 'yawOk', label: t('gateYaw') },
    { key: 'mouthOk', label: t('gateMouth') },
    { key: 'sizeOk', label: t('gateSize') },
    { key: 'lightOk', label: t('gateLight') },
  ];

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', width: '100%' }}>
      {/* Privacy note is permanent — it IS the product promise. */}
      <p
        style={{
          border: '1px solid var(--grat-2)',
          background: 'var(--shelf)',
          color: 'var(--muted)',
          padding: '10px 13px',
          fontSize: 12.5,
          lineHeight: 1.55,
          margin: '0 0 14px',
        }}
      >
        <b style={{ color: 'var(--parchment)', fontWeight: 500 }}>🔒 </b>
        {t('privacy')}
      </p>

      {phase !== 'done' && (
        <div style={{ position: 'relative', border: '1px solid var(--grat-2)', background: 'var(--abyss)' }}>
          <video
            ref={videoRef}
            playsInline
            muted
            style={{ display: 'block', width: '100%', transform: 'scaleX(-1)' }}
            aria-label={t('videoLabel')}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} aria-hidden="true" />
          {phase === 'scanning' && (
            <div
              className="num"
              style={{
                position: 'absolute', left: 10, bottom: 9,
                background: 'var(--abyss)', border: '1px solid var(--grat-2)',
                color: 'var(--brass)', fontSize: 11, padding: '3px 8px', letterSpacing: '.04em',
              }}
            >
              {t('captured', { n: captured, total: TARGET_FRAMES })}
            </div>
          )}
        </div>
      )}

      <div role="status" aria-live="polite" style={{ marginTop: 14 }}>
        {phase === 'idle' && (
          <button
            onClick={start}
            style={{
              width: '100%', background: 'var(--brass)', color: 'var(--abyss)', border: 0,
              fontFamily: 'var(--font-ui)', fontWeight: 600, padding: 11,
              letterSpacing: '.02em', cursor: 'pointer',
            }}
          >
            {t('start')}
          </button>
        )}
        {phase === 'loading' && (
          <p className="num" style={{ color: 'var(--muted)', fontSize: 12, letterSpacing: '.04em' }}>
            {t('loading')}
          </p>
        )}
        {phase === 'scanning' && (
          <ul
            aria-label={t('gatesLabel')}
            style={{
              listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 1,
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              border: '1px solid var(--grat-2)', background: 'var(--grat-1)',
            }}
          >
            {gateItems.map(({ key, label }) => (
              <li
                key={key}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  background: 'var(--panel)', padding: '9px 11px',
                  fontFamily: 'var(--font-data)', fontSize: 11.5, letterSpacing: '.03em',
                  color: gates[key] ? 'var(--brass)' : 'var(--dim)',
                }}
              >
                <span aria-hidden="true">{gates[key] ? '✓' : '○'}</span>
                {label}
              </li>
            ))}
          </ul>
        )}
        {phase === 'analyzing' && (
          <p className="num" style={{ color: 'var(--muted)', fontSize: 12, letterSpacing: '.04em' }}>
            {t('analyzing')}
          </p>
        )}
        {phase === 'error' && (
          <div
            style={{
              border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)',
              color: 'var(--notice-ink)', padding: '11px 13px', fontSize: 13, lineHeight: 1.5,
            }}
          >
            <p style={{ margin: 0 }}>{error}</p>
            <button
              onClick={start}
              style={{
                marginTop: 11, background: 'var(--brass)', color: 'var(--abyss)', border: 0,
                fontFamily: 'var(--font-ui)', fontWeight: 600, fontSize: 13,
                padding: '7px 16px', cursor: 'pointer',
              }}
            >
              {t('retry')}
            </button>
          </div>
        )}
      </div>

      {phase === 'done' && result && (
        <section aria-label={t('reportLabel')}>
          <div style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px' }}>
            <span className="eyebrow" style={{ display: 'block' }}>{t('resultType')}</span>
            <h2 className="display" style={{ fontSize: 26, margin: '6px 0 0', color: 'var(--parchment)' }}>
              {result.primary_element} <em style={{ fontStyle: 'italic', color: 'var(--brass)' }}>
                + {result.secondary_element}
              </em>
            </h2>
            <p className="num" style={{ margin: '8px 0 0', fontSize: 11.5, color: 'var(--dim)' }}>
              {t('framesUsed', {
                used: result.frames_used,
                skipped: result.skipped.length,
              })}
            </p>
          </div>

          {/* The backend's own reconciled verdicts. This block was dropped
              entirely by the old UI, which showed only the raw readings —
              i.e. it hid the layer the server trusts most and displayed the
              one it flags as lens-sensitive. */}
          {result.traits?.length > 0 && (
            <div style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px', marginTop: 12 }}>
              <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>
                {ru ? 'сводные оценки' : 'reconciled verdicts'}
              </span>
              {result.traits.map((tr, i) => (
                <div
                  key={tr.dimension}
                  style={{
                    borderTop: i ? '1px solid var(--grat-1)' : 0,
                    paddingTop: i ? 9 : 0,
                    marginTop: i ? 9 : 0,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
                    <span style={{ fontSize: 13.5, color: 'var(--parchment)' }}>{tr.label}</span>
                    <span className="num" style={{ fontSize: 11.5, color: 'var(--brass)', whiteSpace: 'nowrap' }}>
                      {tr.verdict_label}
                      {tr.conflicted ? ' ±' : ''}
                    </span>
                  </div>
                  {tr.evidence?.length > 0 && (
                    <p className="num" style={{ margin: '4px 0 0', fontSize: 10.5, color: 'var(--dim)', lineHeight: 1.5 }}>
                      {tr.evidence.join(' · ')}
                    </p>
                  )}
                  {/* What is missing is stated, not hidden behind a blank. */}
                  {tr.needed?.length > 0 && (
                    <p style={{ margin: '4px 0 0', fontSize: 11.5, color: 'var(--notice-ink)', lineHeight: 1.45 }}>
                      {tr.needed.join('; ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Lens-robust deviations — the honest headline (no width family). */}
          {result.signature?.length > 0 && (
            <div style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px', marginTop: 12 }}>
              <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>
                {ru ? 'подпись лица · устойчиво к ракурсу' : 'face signature · lens-robust'}
              </span>
              <table className="num" style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: 11.5 }}>
                <tbody>
                  {result.signature.map((s) => (
                    <tr key={s.metric} style={{ borderTop: '1px solid var(--grat-1)' }}>
                      <td style={{ padding: '5px 6px 5px 0', color: 'var(--parchment)' }}>{s.metric}</td>
                      <td style={{ padding: '5px 6px 5px 0', textAlign: 'right', color: 'var(--muted)' }}>
                        {s.median.toFixed(4)}
                      </td>
                      <td style={{ padding: '5px 0', textAlign: 'right', color: 'var(--brass)', whiteSpace: 'nowrap' }}>
                        {s.deviation_units > 0 ? '+' : ''}
                        {s.deviation_units.toFixed(2)} σ
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result.lens_note && (
            <p style={{ marginTop: 12, fontSize: 12, lineHeight: 1.5, color: 'var(--notice-ink)', maxWidth: '66ch' }}>
              {result.lens_note}
            </p>
          )}

          <ul style={{ listStyle: 'none', margin: '12px 0 0', padding: 0 }}>
            {result.readings.map((r) => {
              // A "background" reading is one the backend flags as
              // lens-sensitive. Showing it identically to a robust one is what
              // made the display contradict the server's own reliability model.
              const background = r.scope === 'background';
              return (
                <li
                  key={r.topic}
                  style={{
                    border: `1px solid ${background ? 'var(--grat-1)' : 'var(--grat-2)'}`,
                    background: background ? 'transparent' : 'var(--shelf)',
                    padding: '11px 14px',
                    marginBottom: 8,
                  }}
                >
                  {background && (
                    <span className="eyebrow" style={{ display: 'block', marginBottom: 5 }}>
                      {ru ? 'фон · зависит от ракурса' : 'background · lens-sensitive'}
                    </span>
                  )}
                  <p
                    style={{
                      margin: 0,
                      fontSize: 13.5,
                      lineHeight: 1.55,
                      color: background ? 'var(--muted)' : 'var(--parchment)',
                    }}
                  >
                    {r.text}
                  </p>
                  {/* Source and confidence stay attached to the claim — the
                      reading is a tradition, the measurement behind it is not. */}
                  <p className="num" style={{ margin: '7px 0 0', fontSize: 10.5, color: 'var(--dim)' }}>
                    {r.source} · {r.confidence}
                    {r.support ? ` · ${t('support')}: ${r.support}` : ''}
                  </p>
                </li>
              );
            })}
          </ul>

          <div style={{ border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px', marginTop: 12 }}>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 9 }}>
              {t('coverageTitle')}
            </span>
            <dl style={{ margin: 0 }}>
              {Object.entries(result.coverage).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 8 }}>
                  <dt className="num" style={{ fontSize: 11, color: 'var(--brass)', letterSpacing: '.04em' }}>
                    {t(`coverage_${k}`)}
                  </dt>
                  <dd style={{ margin: '2px 0 0', fontSize: 12.5, lineHeight: 1.5, color: 'var(--muted)' }}>
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <p style={{ marginTop: 14, fontSize: 12.5, lineHeight: 1.55, color: 'var(--muted)', maxWidth: '66ch' }}>
            {result.disclaimer}
          </p>

          <button
            onClick={start}
            style={{
              marginTop: 14, width: '100%', background: 'transparent', color: 'var(--brass)',
              border: '1px solid var(--brass-dim)', fontFamily: 'var(--font-ui)', fontWeight: 600,
              padding: 11, letterSpacing: '.02em', cursor: 'pointer',
            }}
          >
            {t('rescan')}
          </button>
        </section>
      )}
    </div>
  );
}
