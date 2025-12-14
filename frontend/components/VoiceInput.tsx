'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
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
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
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
      if (state === 'listening') {
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
  }, [isSupported, language, onTranscript, state, t]);

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

  // Size classes
  const sizeClasses = {
    sm: 'w-12 h-12 text-xl',
    md: 'w-16 h-16 text-2xl',
    lg: 'w-20 h-20 text-3xl',
  };

  const buttonSize = sizeClasses[size];

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      {/* Main button */}
      <motion.button
        onClick={handleClick}
        disabled={state === 'processing'}
        className={`
          ${buttonSize}
          rounded-full
          flex items-center justify-center
          transition-all duration-300
          disabled:opacity-50 disabled:cursor-not-allowed
          focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-offset-slate-900
          ${
            state === 'listening'
              ? 'bg-red-500 hover:bg-red-600 focus:ring-red-500/50'
              : state === 'error'
              ? 'bg-amber-500 hover:bg-amber-600 focus:ring-amber-500/50'
              : 'bg-gradient-to-br from-rose-500 to-pink-600 hover:from-rose-600 hover:to-pink-700 focus:ring-rose-500/50'
          }
        `}
        whileTap={{ scale: 0.95 }}
        aria-label={state === 'listening' ? t('stop') : t('start')}
      >
        <AnimatePresence mode="wait">
          {state === 'listening' ? (
            <motion.div
              key="recording"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              className="relative"
            >
              {/* Pulsing animation */}
              <motion.div
                className="absolute inset-0 rounded-full bg-white/30"
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.5, 0, 0.5],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
              {/* Stop icon */}
              <div className="w-5 h-5 bg-white rounded-sm" />
            </motion.div>
          ) : state === 'processing' ? (
            <motion.div
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Spinner */}
              <motion.div
                className="w-6 h-6 border-2 border-white border-t-transparent rounded-full"
                animate={{ rotate: 360 }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  ease: 'linear',
                }}
              />
            </motion.div>
          ) : (
            <motion.span
              key="mic"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              🎤
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Status text */}
      <AnimatePresence mode="wait">
        {state === 'listening' && (
          <motion.p
            key="listening"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="text-rose-400 text-sm font-medium"
          >
            {t('listening')}
          </motion.p>
        )}

        {state === 'processing' && (
          <motion.p
            key="processing"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="text-slate-400 text-sm"
          >
            {t('processing')}
          </motion.p>
        )}

        {state === 'error' && errorMessage && (
          <motion.p
            key="error"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="text-amber-400 text-sm text-center max-w-[200px]"
          >
            {errorMessage}
          </motion.p>
        )}

        {state === 'idle' && !isSupported && (
          <motion.p
            key="not-supported"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-slate-500 text-sm text-center max-w-[200px]"
          >
            {t('notSupported')}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
