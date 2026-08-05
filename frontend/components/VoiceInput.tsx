'use client';

/**
 * Voice input — instrument styling.
 *
 * The speech-recognition logic below is unchanged; only the presentation was
 * rebuilt. It used to be a rose→pink gradient circle with framer-motion
 * springs: the last visibly old element left sitting on the rebuilt /dreams
 * screen. Now it is a bordered square in the token palette (brass is the only
 * accent, radius 0, borders not shadows), the pulse is a CSS keyframe — so the
 * global prefers-reduced-motion rule in tokens.css actually silences it — and
 * framer-motion is gone from this component entirely.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import type {
  SpeechRecognition,
  SpeechRecognitionErrorEvent,
  SpeechRecognitionEvent,
} from '../types/web-speech';

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  language?: 'ru' | 'en';
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

type RecordingState = 'idle' | 'listening' | 'processing' | 'error';

const SIZE_PX: Record<NonNullable<VoiceInputProps['size']>, number> = {
  sm: 38,
  md: 46,
  lg: 56,
};

export default function VoiceInput({
  onTranscript,
  language = 'ru',
  className = '',
  size = 'md',
}: VoiceInputProps) {
  const t = useTranslations('VoiceInput');
  const [state, setState] = useState<RecordingState>('idle');
  const [isSupported, setIsSupported] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const transcriptRef = useRef<string>('');
  const stateRef = useRef<RecordingState>('idle');

  // Keep stateRef in sync with state
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Check if Web Speech API is supported
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setIsSupported(false);
      }
    }
  }, []);

  const startRecording = useCallback(() => {
    if (!isSupported) {
      setState('error');
      setErrorMessage(t('notSupported'));
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = language === 'ru' ? 'ru-RU' : 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setState('listening');
      transcriptRef.current = '';
      setErrorMessage(null);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        }
      }

      if (finalTranscript) {
        transcriptRef.current += finalTranscript;
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('Speech recognition error:', event.error);

      if (event.error === 'not-allowed') {
        setState('error');
        setErrorMessage(t('error'));
      } else {
        setState('idle');
      }
    };

    recognition.onend = () => {
      // Use ref to get current state (avoids stale closure)
      if (stateRef.current === 'listening') {
        setState('processing');

        // Short delay to simulate processing
        setTimeout(() => {
          if (transcriptRef.current.trim()) {
            onTranscript(transcriptRef.current.trim());
          }
          setState('idle');
        }, 500);
      }
    };

    try {
      recognition.start();
    } catch (err) {
      console.error('Failed to start recognition:', err);
      setState('error');
      setErrorMessage(t('error'));
    }
  }, [isSupported, language, onTranscript, t]);

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, []);

  const handleClick = useCallback(() => {
    if (state === 'listening') {
      stopRecording();
    } else if (state === 'idle' || state === 'error') {
      startRecording();
    }
  }, [state, startRecording, stopRecording]);

  const px = SIZE_PX[size];
  const listening = state === 'listening';

  return (
    <div className={`flex flex-col items-center ${className}`} style={{ gap: 6 }}>
      <button
        type="button"
        onClick={handleClick}
        disabled={state === 'processing'}
        aria-label={listening ? t('stop') : t('start')}
        className={listening ? 'rec-pulse' : undefined}
        style={{
          width: px,
          height: px,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: listening ? 'var(--brass)' : 'transparent',
          border: `1px solid ${
            state === 'error' ? 'var(--brass-dim)' : 'var(--grat-2)'
          }`,
          color: listening ? 'var(--abyss)' : 'var(--brass)',
          cursor: state === 'processing' ? 'not-allowed' : 'pointer',
          opacity: state === 'processing' ? 0.45 : 1,
          transition: 'background .15s ease, color .15s ease',
        }}
      >
        {listening ? (
          // Stop: a filled square. An instrument reads as a control, not a toy.
          <span
            aria-hidden="true"
            style={{ width: px * 0.28, height: px * 0.28, background: 'var(--abyss)' }}
          />
        ) : state === 'processing' ? (
          <span className="num" aria-hidden="true" style={{ fontSize: px * 0.32 }}>
            …
          </span>
        ) : (
          <span aria-hidden="true" style={{ fontSize: px * 0.42, lineHeight: 1 }}>
            ◉
          </span>
        )}
      </button>

      {/* Status line — mono, like every other service label on the screen. */}
      {(listening || state === 'processing' || (state === 'error' && errorMessage)
        || (state === 'idle' && !isSupported)) && (
        <p
          className="num"
          style={{
            margin: 0,
            fontSize: 10.5,
            letterSpacing: '.04em',
            textAlign: 'center',
            maxWidth: 190,
            color:
              state === 'error' || !isSupported
                ? 'var(--notice-ink)'
                : listening
                ? 'var(--brass)'
                : 'var(--dim)',
          }}
        >
          {listening
            ? t('listening')
            : state === 'processing'
            ? t('processing')
            : state === 'error'
            ? errorMessage
            : t('notSupported')}
        </p>
      )}
    </div>
  );
}
