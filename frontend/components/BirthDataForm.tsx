'use client';

/**
 * Birth-data entry, shared by /natal and /astrocartography.
 *
 * A sentence with blanks rather than a stack of labelled boxes — the design
 * system's editorial register, and it also happens to be the honest shape:
 * birth data IS one sentence. Picking the city fills latitude and longitude
 * from the geocoder, so what used to be six fields (date, time, lat, lon,
 * place, timezone) is three blanks plus an optional coordinate override.
 *
 * The timezone dropdown is gone entirely. It offered six zones and asked the
 * user to know which offset applied in their birth year; the server derives
 * the zone from the coordinates with historical rules, and the zone it
 * actually used is displayed afterwards from the response.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import CityAutocomplete from '@/components/CityAutocomplete';
import {
  EMPTY_BIRTH,
  birthIssues,
  loadBirth,
  saveBirth,
  type BirthData,
} from '@/lib/birth-data';

type Lang = 'ru' | 'en';

interface Props {
  lang: Lang;
  busy?: boolean;
  submitLabel: string;
  busyLabel: string;
  onSubmit: (b: BirthData) => void;
  /** Rendered under the button — notices, refusals, quota messages. */
  children?: React.ReactNode;
}

function copy(lang: Lang) {
  const ru = {
    eyebrow: 'Ваши данные',
    lead: 'Моё рождение —',
    on: 'в',
    at: 'в',
    datePh: 'дата',
    timePh: 'время',
    cityPh: 'город',
    timeUnknown: 'время неизвестно',
    timeUnknownNote:
      'Без времени считаются только положения планет. Дома, Асцендент и '
      + 'астрокартографические линии зависят от времени и показаны не будут.',
    coords: 'Координаты',
    edit: 'уточнить вручную',
    hide: 'свернуть',
    lat: 'широта',
    lon: 'долгота',
    resolved: 'из справочника городов',
    manual: 'введено вручную',
    tzNote: 'Часовой пояс определит сервер по координатам — с историческими правилами того года.',
    fix: 'Чтобы построить карту:',
    forget: 'Забыть мои данные',
    forgotten: 'Данные удалены с этого устройства.',
    stored: 'Данные хранятся только в этом браузере.',
  };
  const en = {
    eyebrow: 'Your data',
    lead: 'I was born on',
    on: 'on',
    at: 'at',
    datePh: 'date',
    timePh: 'time',
    cityPh: 'city',
    timeUnknown: 'time unknown',
    timeUnknownNote:
      'Without a time only planet positions are computed. Houses, the '
      + 'Ascendant and astrocartography lines depend on it and will not be shown.',
    coords: 'Coordinates',
    edit: 'set manually',
    hide: 'collapse',
    lat: 'latitude',
    lon: 'longitude',
    resolved: 'from the city index',
    manual: 'entered by hand',
    tzNote: 'The server derives the timezone from the coordinates, with that year\'s historical rules.',
    fix: 'To build the chart:',
    forget: 'Forget my data',
    forgotten: 'Data removed from this device.',
    stored: 'Kept in this browser only.',
  };
  return lang === 'ru' ? ru : en;
}

export default function BirthDataForm({
  lang, busy = false, submitLabel, busyLabel, onSubmit, children,
}: Props) {
  const t = copy(lang);
  const [b, setB] = useState<BirthData>(EMPTY_BIRTH);
  const [showCoords, setShowCoords] = useState(false);
  const [coordSource, setCoordSource] = useState<'city' | 'manual' | null>(null);
  const [forgotten, setForgotten] = useState(false);
  const [tried, setTried] = useState(false);
  const restored = useRef(false);

  // Restore on mount only. Reading in useState's initialiser would run on the
  // server during SSR, where localStorage does not exist.
  useEffect(() => {
    const saved = loadBirth();
    if (saved) {
      setB(saved);
      if (saved.lat && saved.lon) setCoordSource('city');
    }
    restored.current = true;
  }, []);

  useEffect(() => {
    if (restored.current && (b.date || b.place || b.lat)) saveBirth(b);
  }, [b]);

  const issues = useMemo(() => birthIssues(b, lang), [b, lang]);
  const set = (patch: Partial<BirthData>) => {
    setForgotten(false);
    setB((prev) => ({ ...prev, ...patch }));
  };

  function submit(ev: React.FormEvent) {
    ev.preventDefault();
    setTried(true);
    if (issues.length) return;
    onSubmit(b);
  }

  return (
    <form onSubmit={submit} className="panel-block">
      <div className="eyebrow" style={{ marginBottom: 9 }}>{t.eyebrow}</div>

      {/* The sentence. Inputs sit inline, underlined rather than boxed. */}
      <p className="birth-sentence">
        {t.lead}{' '}
        <input
          type="date"
          aria-label={t.datePh}
          value={b.date}
          onChange={(e) => set({ date: e.target.value })}
          className="blank blank-date"
        />
        {b.timeKnown ? (
          <>
            {' '}{t.at}{' '}
            <input
              type="time"
              aria-label={t.timePh}
              value={b.time}
              onChange={(e) => set({ time: e.target.value })}
              className="blank blank-time"
            />
          </>
        ) : (
          <> <span className="blank-static">{t.timeUnknown}</span></>
        )}
        {' '}{t.on}{' '}
      </p>

      <div style={{ marginTop: 2 }}>
        <CityAutocomplete
          value={b.place}
          locale={lang}
          disabled={busy}
          placeholder={t.cityPh}
          onChange={(v) => {
            // Typing a new name invalidates coordinates resolved for the old
            // one — otherwise a half-edited name keeps the previous city's
            // position and quietly charts the wrong place.
            if (coordSource === 'city') {
              set({ place: v, lat: '', lon: '' });
              setCoordSource(null);
            } else {
              set({ place: v });
            }
          }}
          onCitySelect={(city) => {
            set({ place: city.display || city.name, lat: String(city.lat), lon: String(city.lon) });
            setCoordSource('city');
          }}
        />
      </div>

      <label className="birth-toggle">
        <input
          type="checkbox"
          checked={!b.timeKnown}
          onChange={(e) => set({ timeKnown: !e.target.checked, time: e.target.checked ? '' : b.time })}
        />
        <span>{t.timeUnknown}</span>
      </label>
      {!b.timeKnown && <p className="birth-note">{t.timeUnknownNote}</p>}

      {/* Coordinates: a readout once resolved, editable on demand. They are
          the thing that actually decides the chart, so they are never hidden
          — only the input boxes are. */}
      <div className="birth-coords">
        <div className="birth-coords-head">
          <span className="eyebrow" style={{ margin: 0 }}>{t.coords}</span>
          <button type="button" className="birth-link" onClick={() => setShowCoords((v) => !v)}>
            {showCoords ? t.hide : t.edit}
          </button>
        </div>

        {showCoords ? (
          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <Field label={t.lat}>
              <input
                type="number" step="0.0001" min={-90} max={90} value={b.lat}
                onChange={(e) => { set({ lat: e.target.value }); setCoordSource('manual'); }}
                className="birth-input"
              />
            </Field>
            <Field label={t.lon}>
              <input
                type="number" step="0.0001" min={-180} max={180} value={b.lon}
                onChange={(e) => { set({ lon: e.target.value }); setCoordSource('manual'); }}
                className="birth-input"
              />
            </Field>
          </div>
        ) : (
          <div className="birth-readout">
            {b.lat && b.lon ? (
              <>
                {fmtLat(Number(b.lat))} · {fmtLon(Number(b.lon))}
                <span className="birth-src">
                  {coordSource === 'manual' ? t.manual : t.resolved}
                </span>
              </>
            ) : <span className="birth-src" style={{ marginLeft: 0 }}>—</span>}
          </div>
        )}
        <p className="birth-note">{t.tzNote}</p>
      </div>

      <button type="submit" disabled={busy} className="birth-submit">
        {busy ? busyLabel : submitLabel}
      </button>

      {tried && issues.length > 0 && (
        <div className="birth-issues">
          <b>{t.fix}</b>
          <ul>{issues.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      )}

      {children}

      <div className="birth-foot">
        <span>{forgotten ? t.forgotten : t.stored}</span>
        <button
          type="button"
          className="birth-link"
          onClick={() => {
            setB(EMPTY_BIRTH);
            setCoordSource(null);
            setTried(false);
            setForgotten(true);
            try { window.localStorage.removeItem('oneiro.birth.v1'); } catch { /* see birth-data */ }
          }}
        >
          {t.forget}
        </button>
      </div>
    </form>
  );
}

const fmtLat = (v: number) => `${Math.abs(v).toFixed(4)}°${v >= 0 ? 'N' : 'S'}`;
const fmtLon = (v: number) => `${Math.abs(v).toFixed(4)}°${v >= 0 ? 'E' : 'W'}`;

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <label className="birth-flabel">{label}</label>
      {children}
    </div>
  );
}
