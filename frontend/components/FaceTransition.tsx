'use client';

/**
 * The hand-off at the bottom of a finished face reading.
 *
 * Three things about it are deliberate, and each one is a conversion decision
 * rather than a layout preference:
 *
 * 1. It sits AFTER the complete result, never before it. The reading is free
 *    and whole; nothing is withheld and nothing is teased. A barrier in front
 *    of a first result costs more than it collects, so the offer arrives at
 *    the one moment the person is already satisfied.
 *
 * 2. It is a COMPARISON, not a purchase. "A face does not change. The sky
 *    changes every day." The next step is presented as the more interesting
 *    question, which is also true — the chart is the instrument, this was the
 *    entrance.
 *
 * 3. The birth-data form is HERE, on this screen, not behind a "try it"
 *    click. Every extra page between the intent and the input costs roughly
 *    half the people who had the intent. `BirthDataForm` persists to
 *    localStorage as it is typed, so /natal picks the answer up with no query
 *    string and computes immediately — the input is not re-asked.
 *
 * No email is requested anywhere on this path. That belongs at the quota
 * boundary, not at the moment of interest.
 */

import { useRouter } from 'next/navigation';
import BirthDataForm from '@/components/BirthDataForm';
import type { BirthData } from '@/lib/birth-data';
import { track } from '@/lib/metrics';

type Lang = 'ru' | 'en';

function copy(lang: Lang) {
  const ru = {
    eyebrow: 'дальше',
    lead: 'Лицо не меняется.',
    turn: 'Небо меняется каждый день.',
    ask: 'Посмотрим, каким оно было в момент вашего рождения?',
    build: 'Построить карту',
    building: 'Считаем…',
  };
  const en = {
    eyebrow: 'next',
    lead: 'A face does not change.',
    turn: 'The sky changes every day.',
    ask: 'Shall we look at the one you were born under?',
    build: 'Build the chart',
    building: 'Computing…',
  };
  return lang === 'ru' ? ru : en;
}

export default function FaceTransition({ lang }: { lang: Lang }) {
  const router = useRouter();
  const t = copy(lang);

  // The form has already written the data to localStorage by the time submit
  // fires, so the chart screen needs no parameters — it restores and computes.
  //
  // This submit IS the funnel's conversion: a free reading was read to the end
  // and the person answered with their birth date. Counted anonymously — the
  // date itself never goes to the counter, only that one was entered.
  const go = (_b: BirthData) => {
    track('birth_date_entered');
    router.push(`/${lang}/natal`);
  };

  return (
    <section
      aria-label={t.ask}
      style={{
        border: '1px solid var(--grat-2)',
        background: 'var(--shelf)',
        marginTop: 'clamp(20px,3vw,34px)',
      }}
    >
      <div style={{ padding: '15px 15px 0' }}>
        <span className="eyebrow" style={{ display: 'block' }}>{t.eyebrow}</span>
        <p
          className="display"
          style={{
            fontSize: 'clamp(19px,2.6vw,25px)',
            lineHeight: 1.35,
            margin: '7px 0 0',
            color: 'var(--parchment)',
            maxWidth: '30ch',
          }}
        >
          {t.lead}{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--brass)' }}>{t.turn}</em>
        </p>
        <p
          style={{
            margin: '9px 0 0',
            fontSize: 13.5,
            lineHeight: 1.55,
            color: 'var(--muted)',
            maxWidth: '46ch',
          }}
        >
          {t.ask}
        </p>
      </div>

      <BirthDataForm
        lang={lang}
        submitLabel={t.build}
        busyLabel={t.building}
        onSubmit={go}
      />
    </section>
  );
}
