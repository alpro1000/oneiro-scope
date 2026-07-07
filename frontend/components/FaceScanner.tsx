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
import { topicTitle } from '../lib/physiognomy-topics';
import FindingCard from './FindingCard';

const VERDICT_STYLE: Record<string, string> = {
  high: 'border-gold bg-goldSoft text-goldStrong',
  lean_high: 'border-gold/60 bg-surfaceStrong text-goldStrong',
  lean_low: 'border-border bg-surfaceStrong text-inkMuted',
  low: 'border-border bg-surfaceStrong text-inkMuted',
  unclear: 'border-danger/50 bg-danger/10 text-danger',
};

const TARGET_FRAMES = 5;
const CAPTURE_SPACING_MS = 600; // spread captures over distinct moments
const WASM_BASE =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm';
const MODEL_URL =
  process.env.NEXT_PUBLIC_FACE_MODEL_URL ||
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

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
      const [{ FaceLandmarker, FilesetResolver }, stream] = await Promise.all([
        import('@mediapipe/tasks-vision'),
        navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 } },
          audio: false,
        }),
      ]);
      const fileset = await FilesetResolver.forVisionTasks(WASM_BASE);
      landmarkerRef.current = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL },
        runningMode: 'VIDEO',
        numFaces: 1,
      });
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

  // A reading's `text` is already the composed dictionary clause (no
  // separate quote/gloss split exists in the API) — same honest
  // minimal-card choice as dream symbols: measurement + quote, no
  // fabricated human paraphrase or plus/minus.
  const readingCardProps = (r: ArchiveResponse['readings'][number]) => ({
    title: topicTitle(r.topic, locale),
    seenText: r.support
      ? `${t('support')}: ${r.support}`
      : (locale === 'ru' ? 'из анкеты' : 'from questionnaire'),
    traditionQuote: r.text,
    traditionSource: `${r.source} · ${r.confidence}`,
    lifeContext: r.life_context,
  });

  const personalReadings = result?.readings.filter((r) => r.scope !== 'background') ?? [];
  const backgroundReadings = result?.readings.filter((r) => r.scope === 'background') ?? [];

  return (
    <div className="mx-auto w-full max-w-2xl">
      {/* Privacy note is permanent — it IS the product promise. */}
      <p className="mb-4 rounded-lg border border-goldSoft bg-goldSoft p-3 text-sm text-ink">
        🔒 {t('privacy')}
      </p>

      {phase !== 'done' && (
        <div className="relative overflow-hidden rounded-2xl" style={{background: 'var(--cam-bg)', border: '1px solid var(--cam-border)'}}>
          <video
            ref={videoRef}
            playsInline
            muted
            className="w-full -scale-x-100"
            aria-label={t('videoLabel')}
          />
          <canvas ref={canvasRef} className="hidden" aria-hidden="true" />
          {phase === 'scanning' && (
            <div
              className="absolute bottom-2 left-2 rounded-full px-3 py-1 font-mono text-sm"
              style={{background: 'var(--cam-caption-bg)', color: 'var(--cam-accent)'}}
            >
              {t('captured', { n: captured, total: TARGET_FRAMES })}
            </div>
          )}
        </div>
      )}

      <div role="status" aria-live="polite" className="mt-4">
        {phase === 'idle' && (
          <button
            onClick={start}
            className="w-full rounded-full bg-gold px-6 py-3 font-semibold text-bgDeep transition-colors hover:bg-goldStrong focus:outline-none focus:ring-2 focus:ring-gold"
          >
            {t('start')}
          </button>
        )}
        {phase === 'loading' && (
          <p className="animate-pulse text-inkMuted">{t('loading')}</p>
        )}
        {phase === 'scanning' && (
          <ul className="grid gap-1 sm:grid-cols-2" aria-label={t('gatesLabel')}>
            {gateItems.map(({ key, label }) => (
              <li
                key={key}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  gates[key]
                    ? 'bg-goldSoft text-goldStrong'
                    : 'bg-surfaceStrong text-inkFaint'
                }`}
              >
                <span aria-hidden="true">{gates[key] ? '✓' : '○'}</span>
                {label}
              </li>
            ))}
          </ul>
        )}
        {phase === 'analyzing' && (
          <p className="animate-pulse text-inkMuted">{t('analyzing')}</p>
        )}
        {phase === 'error' && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-danger">
            <p>{error}</p>
            <button
              onClick={start}
              className="mt-3 rounded-full bg-danger/80 px-4 py-2 text-sm font-medium text-ink hover:bg-danger"
            >
              {t('retry')}
            </button>
          </div>
        )}
      </div>

      {phase === 'done' && result && (
        <section aria-label={t('reportLabel')}>
          <div className="mb-6 rounded-xl border border-border bg-surface p-4">
            <h2 className="font-display text-lg font-semibold text-ink">
              {t('resultType')}:{' '}
              <span className="text-goldStrong">
                {result.primary_element} + {result.secondary_element}
              </span>
            </h2>
            <p className="mt-1 text-sm text-inkMuted">
              {t('framesUsed', {
                used: result.frames_used,
                skipped: result.skipped.length,
              })}
            </p>
          </div>

          {/* Trait verdicts — the weighted consensus, not the raw
              (sometimes conflicting) dictionary clauses. */}
          {result.traits.length > 0 && (
            <div className="mb-6 rounded-xl border border-border bg-surface p-4">
              <h3 className="mb-3 font-mono text-xs uppercase tracking-widest text-inkFaint">
                {t('traitsTitle')}
              </h3>
              <ul className="space-y-2">
                {result.traits.map((trait) => (
                  <li
                    key={trait.dimension}
                    className={`rounded-lg border px-3 py-2 ${VERDICT_STYLE[trait.verdict] || VERDICT_STYLE.unclear}`}
                  >
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <span className="font-display font-semibold">{trait.label}</span>
                      <span className="font-mono text-xs uppercase tracking-wide">
                        {trait.verdict_label} · {trait.score >= 0 ? '+' : ''}{trait.score.toFixed(2)}
                      </span>
                    </div>
                    {trait.evidence.length > 0 && (
                      <p className="mt-1 font-mono text-xs text-inkMuted">
                        {trait.evidence
                          .map((e) => `${e.contribution >= 0 ? '+' : ''}${e.contribution} ${e.clause}`)
                          .join(' · ')}
                      </p>
                    )}
                    {trait.needed.map((n, i) => (
                      <p key={i} className="mt-1 text-xs text-inkMuted">
                        ⚠ {t('needed')}: {n}
                      </p>
                    ))}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Findings — measurement + cited dictionary clause; no
              fabricated human gloss or plus/minus (the API doesn't
              carry that split for physiognomy readings). */}
          {personalReadings.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-3 font-mono text-xs uppercase tracking-widest text-inkFaint">
                {t('findingsTitle')}
              </h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {personalReadings.map((r) => (
                  <FindingCard key={r.topic} {...readingCardProps(r)} />
                ))}
              </div>
            </div>
          )}

          {/* Background — lens-sensitive, not personal (see lens_note). */}
          {backgroundReadings.length > 0 && (
            <div className="mb-6 rounded-xl border border-dashed border-border bg-surface/60 p-4">
              <h3 className="mb-2 font-mono text-xs uppercase tracking-widest text-inkFaint">
                🌫 {t('backgroundTitle')}
              </h3>
              <ul className="space-y-1 text-sm text-inkMuted">
                {backgroundReadings.map((r) => (
                  <li key={r.topic}>{r.text}</li>
                ))}
              </ul>
              {result.lens_note && (
                <p className="mt-2 text-xs text-inkFaint">{result.lens_note}</p>
              )}
            </div>
          )}

          <div className="rounded-xl border border-border bg-surface/40 p-4">
            <h3 className="mb-2 font-mono text-xs uppercase tracking-widest text-inkFaint">
              {t('coverageTitle')}
            </h3>
            <dl className="space-y-2 text-sm">
              {Object.entries(result.coverage).map(([k, v]) => (
                <div key={k}>
                  <dt className="font-medium text-inkMuted">
                    {t(`coverage_${k}`)}
                  </dt>
                  <dd className="text-inkFaint">{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <p className="mt-6 text-xs leading-relaxed text-inkFaint">
            {result.disclaimer}
          </p>

          <button
            onClick={start}
            className="mt-6 w-full rounded-full border border-border bg-surfaceStrong px-6 py-3 font-semibold text-ink transition-colors hover:border-gold focus:outline-none focus:ring-2 focus:ring-gold"
          >
            {t('rescan')}
          </button>
        </section>
      )}
    </div>
  );
}
