'use client';

import {useEffect} from 'react';
import {motion, AnimatePresence} from 'framer-motion';

type Props = {
  isOpen: boolean;
  message?: string;
};

/**
 * Full-screen loading modal that blocks all UI interaction during calculations.
 * Prevents user from clicking other fields or switching tabs.
 */
export default function LoadingModal({isOpen, message = 'Calculating...'}: Props) {
  // Prevent scrolling when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{opacity: 0}}
          animate={{opacity: 1}}
          exit={{opacity: 0}}
          className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 backdrop-blur-sm"
          style={{
            WebkitBackdropFilter: 'blur(8px)',
          }}
        >
          {/* Modal content */}
          <motion.div
            initial={{scale: 0.9, opacity: 0}}
            animate={{scale: 1, opacity: 1}}
            exit={{scale: 0.9, opacity: 0}}
            transition={{delay: 0.1}}
            className="relative mx-4 flex max-w-md flex-col items-center gap-6 rounded-xl border border-gold-soft bg-surface p-8 shadow-gold"
          >
            {/* Spinner */}
            <div className="relative h-16 w-16">
              <div className="absolute inset-0 animate-spin rounded-full border-4 border-gold-soft border-t-gold"></div>
              <div className="absolute inset-2 animate-pulse rounded-full border-2 border-gold/20"></div>
            </div>

            {/* Message */}
            <div className="text-center">
              <h3 className="mb-2 text-lg font-semibold text-ink">{message}</h3>
              <p className="text-sm text-ink-muted">
                Пожалуйста, подождите...
              </p>
            </div>

            {/* Animated dots */}
            <div className="flex gap-2">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="h-2 w-2 rounded-full bg-gold"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5],
                  }}
                  transition={{
                    duration: 1,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
