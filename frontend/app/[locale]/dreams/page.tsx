'use client';

/**
 * Dream analysis — instrument screen.
 *
 * The old version rendered its own duplicate in-page header (which covered the
 * global one), used framer-motion and a hardcoded slate/indigo/purple palette,
 * and — worse — showed only the LLM prose while silently dropping the
 * deterministic layer the product is actually built on: the Hall/Van de Castle
 * structural coding, the per-event evidence clauses behind every count, the
 * norm comparison, the degradation ledger and the disclaimer.
 *
 * Here the split is explicit and visible, in the project's order of confidence:
 *   1. structural coding (confidence 1.0) — counts, each traceable to the exact
 *      clause and the cited 1966 rule that produced it;
 *   2. comparison to the Hall/Van de Castle norms — with units named
 *      (percentage points vs ratio) and "not enough data" said out loud rather
 *      than rendered as a flattering 100%;
 *   3. the symbol dictionary;
 *   4. the LLM synthesis, labelled as interpretation, last.
 * Every number is mono, brass is the only accent, nothing is rounded, and the
 * disclaimer sits next to the result as normal text — not as footer fine print.
 */

import { useState } from 'react';
import { useParams } from 'next/navigation';
import VoiceInput from '../../../components/VoiceInput';
import {
  analyzeDream,
  type DreamAnalysisResponse,
} from '../../../lib/dreams-client';

type Lang = 'ru' | 'en';

const COPY = {
  ru: {
    eyebrow: 'анализ сна · Холл — Ван де Касл',
    titleA: 'Что в нём ',
    titleEm: 'сосчитано',
    lead:
      'Структурное кодирование сна: персонажи, действия, исходы — каждый счётчик '
      + 'привязан к конкретной фразе и правилу кодирования 1966 года. Толкование идёт '
      + 'последним и помечено как толкование.',
    inputLabel: 'Текст сна',
    placeholder: 'Опишите сон так, как он запомнился…',
    dateLabel: 'Дата сна (необязательно)',
    dateHint: 'С датой в разбор добавится лунный контекст',
    analyze: 'Разобрать',
    analyzing: 'Считаем…',
    words: 'слов',
    coding: 'Структурное кодирование',
    characters: 'Персонажи',
    male: 'мужские', female: 'женские', animal: 'животные',
    interactions: 'Взаимодействия',
    friendly: 'дружественные', aggressive: 'агрессивные', sexual: 'сексуальные',
    outcomes: 'Исходы',
    successes: 'успехи', failures: 'неудачи',
    misfortunes: 'несчастья', goodFortunes: 'удачи',
    emotions: 'Эмоции',
    positive: 'положительные', negative: 'отрицательные',
    evidence: 'Доказательства кодирования',
    evidenceHint: 'Каждая строка — фраза, из которой взят счётчик, и правило.',
    norms: 'Сравнение с нормами',
    genderUsed: 'нормы',
    typicality: 'типичность',
    noTypicality: 'не вычислена — ни один показатель не набрал порога данных',
    indicator: 'показатель', yours: 'у вас', norm: 'норма', deviation: 'отклонение',
    basedOn: 'событий в основе',
    pp: 'п.п.',
    symbols: 'Символы',
    emotion: 'Ведущая эмоция',
    intensity: 'интенсивность',
    themes: 'Темы', archetypes: 'Архетипы',
    interpretation: 'Толкование',
    interpretationNote: 'Синтез модели поверх посчитанного выше — не измерение.',
    recommendations: 'Что можно с этим сделать',
    lunar: 'Лунный контекст',
    lunarDay: 'лунный день', phase: 'фаза', moonSign: 'Луна в знаке',
    degraded: 'Неполные данные',
    disclaimerLead: 'Кодирование проверяемо, толкование — традиция.',
    disclaimerFallback:
      'Рефлексивный / развлекательный контент — не медицинская, психологическая, '
      + 'юридическая или финансовая консультация.',
    provCoder: 'кодировщик', provMethod: 'метод', provId: 'id разбора', provAt: 'посчитано',
    errorTitle: 'Разбор не выполнен',
  },
  en: {
    eyebrow: 'dream analysis · Hall — Van de Castle',
    titleA: 'What is ',
    titleEm: 'counted',
    lead:
      'Structural coding of the dream: characters, acts, outcomes — every count is '
      + 'tied to the exact clause and the 1966 coding rule that produced it. '
      + 'Interpretation comes last and is labelled as interpretation.',
    inputLabel: 'Dream text',
    placeholder: 'Describe the dream as you remember it…',
    dateLabel: 'Dream date (optional)',
    dateHint: 'With a date the reading gains lunar context',
    analyze: 'Analyse',
    analyzing: 'Computing…',
    words: 'words',
    coding: 'Structural coding',
    characters: 'Characters',
    male: 'male', female: 'female', animal: 'animal',
    interactions: 'Interactions',
    friendly: 'friendly', aggressive: 'aggressive', sexual: 'sexual',
    outcomes: 'Outcomes',
    successes: 'successes', failures: 'failures',
    misfortunes: 'misfortunes', goodFortunes: 'good fortunes',
    emotions: 'Emotions',
    positive: 'positive', negative: 'negative',
    evidence: 'Coding evidence',
    evidenceHint: 'Each row is the clause a count came from, and the rule.',
    norms: 'Comparison to norms',
    genderUsed: 'norms',
    typicality: 'typicality',
    noTypicality: 'not computed — no indicator met the data threshold',
    indicator: 'indicator', yours: 'yours', norm: 'norm', deviation: 'deviation',
    basedOn: 'events in base',
    pp: 'pp',
    symbols: 'Symbols',
    emotion: 'Leading emotion',
    intensity: 'intensity',
    themes: 'Themes', archetypes: 'Archetypes',
    interpretation: 'Interpretation',
    interpretationNote: 'A model synthesis on top of the counts above — not a measurement.',
    recommendations: 'What you might do with this',
    lunar: 'Lunar context',
    lunarDay: 'lunar day', phase: 'phase', moonSign: 'Moon in sign',
    degraded: 'Incomplete data',
    disclaimerLead: 'The coding is verifiable; the meaning is tradition.',
    disclaimerFallback:
      'Reflective / entertainment content — not medical, psychological, legal or '
      + 'financial advice.',
    provCoder: 'coder', provMethod: 'method', provId: 'analysis id', provAt: 'computed',
    errorTitle: 'Analysis did not run',
  },
} as const;

const EMOTION: Record<string, {ru: string; en: string}> = {
  happiness: {ru: 'радость', en: 'happiness'},
  sadness: {ru: 'печаль', en: 'sadness'},
  anger: {ru: 'гнев', en: 'anger'},
  apprehension: {ru: 'тревога', en: 'apprehension'},
  confusion: {ru: 'смятение', en: 'confusion'},
  neutral: {ru: 'нейтральная', en: 'neutral'},
};

export default function DreamsPage() {
  const params = useParams();
  const lang: Lang = params?.locale === 'ru' ? 'ru' : 'en';
  const locale = (params?.locale as string) || 'ru';
  const t = COPY[lang];

  const [dreamText, setDreamText] = useState('');
  const [dreamDate, setDreamDate] = useState('');
  const [busy, setBusy] = useState(false);
  const [analysis, setAnalysis] = useState<DreamAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onAnalyze() {
    if (!dreamText.trim()) return;
    setBusy(true);
    setError(null);
    setAnalysis(null);
    try {
      setAnalysis(await analyzeDream({
        dream_text: dreamText,
        dream_date: dreamDate || undefined,
        locale,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const a = analysis;
  const ca = a?.content_analysis;
  const norms = a?.norm_comparison;

  return (
    <main style={{padding: 'clamp(14px,2.2vw,30px)', maxWidth: 1100, margin: '0 auto'}}>
      <header style={{paddingBottom: 14, marginBottom: 'clamp(12px,1.6vw,20px)',
        borderBottom: '1px solid var(--grat-1)'}}>
        <span className="eyebrow">{t.eyebrow}</span>
        <h1 style={{fontSize: 'clamp(28px,5vw,52px)', margin: '4px 0 0'}}>
          {t.titleA}<em>{t.titleEm}</em>
        </h1>
        <p style={{color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.6, maxWidth: '62ch', marginTop: 12}}>
          {t.lead}
        </p>
      </header>

      {/* ── input ── */}
      <section style={{border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px'}}>
        <span className="eyebrow" style={{display: 'block', marginBottom: 9}}>{t.inputLabel}</span>
        <textarea
          value={dreamText}
          onChange={(e) => setDreamText(e.target.value)}
          placeholder={t.placeholder}
          rows={7}
          style={{
            width: '100%', background: 'var(--abyss)', color: 'var(--parchment)',
            border: '1px solid var(--grat-2)', fontFamily: 'var(--font-ui)',
            fontSize: 14, lineHeight: 1.6, padding: '9px 11px', resize: 'vertical',
          }}
        />
        <div style={{display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end', marginTop: 10}}>
          <div style={{minWidth: 150}}>
            <label style={labelStyle}>{t.dateLabel}</label>
            <input type="date" value={dreamDate} onChange={(e) => setDreamDate(e.target.value)}
              style={inputStyle} />
          </div>
          <VoiceInput
            onTranscript={(text) => setDreamText((p) => (p ? `${p} ${text}` : text))}
            language={lang}
            size="md"
          />
          <button type="button" onClick={onAnalyze} disabled={busy || !dreamText.trim()}
            style={{
              marginLeft: 'auto', background: 'var(--brass)', color: 'var(--abyss)', border: 0,
              fontFamily: 'var(--font-ui)', fontWeight: 600, padding: '9px 20px',
              letterSpacing: '.02em',
              cursor: busy || !dreamText.trim() ? 'not-allowed' : 'pointer',
              opacity: busy || !dreamText.trim() ? 0.45 : 1,
            }}>
            {busy ? t.analyzing : t.analyze}
          </button>
        </div>
        <p style={{color: 'var(--dim)', fontFamily: 'var(--font-data)', fontSize: 11, marginTop: 7}}>
          {t.dateHint}
        </p>
      </section>

      {error && (
        <div style={{border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)',
          color: 'var(--notice-ink)', padding: '10px 13px', fontSize: 13, marginTop: 14}}>
          <b style={{fontWeight: 600}}>{t.errorTitle}.</b> {error}
        </div>
      )}

      {a && (
        <>
          {/* Degradation ledger — shown, never swallowed (§12). */}
          {a.degraded && a.degraded.length > 0 && (
            <div style={{border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)',
              color: 'var(--notice-ink)', padding: '9px 12px', fontSize: 12.5, marginTop: 14}}>
              <b style={{fontWeight: 600}}>{t.degraded}:</b>{' '}
              <span className="num">{a.degraded.join(' · ')}</span>
            </div>
          )}

          <div className="stage" style={{marginTop: 14}}>
            {/* ── main column ── */}
            <div>
              {a.summary && (
                <section style={panelStyle}>
                  <p style={{fontSize: 15, lineHeight: 1.6, color: 'var(--parchment)', margin: 0}}>
                    {a.summary}
                  </p>
                  <div className="num" style={{marginTop: 10, fontSize: 11.5, color: 'var(--dim)',
                    display: 'flex', gap: 18, flexWrap: 'wrap'}}>
                    <span>{a.word_count} {t.words}</span>
                    {a.primary_emotion && (
                      <span>
                        {t.emotion}: <span style={{color: 'var(--brass)'}}>
                          {EMOTION[a.primary_emotion]?.[lang] || a.primary_emotion}
                        </span>{' '}
                        · {t.intensity} {a.emotion_intensity.toFixed(2)}
                      </span>
                    )}
                  </div>
                </section>
              )}

              {/* Coding evidence — the clause + rule behind each count. */}
              {a.hvdc_evidence && a.hvdc_evidence.length > 0 && (
                <section style={{...panelStyle, marginTop: 12}}>
                  <span className="eyebrow" style={{display: 'block'}}>{t.evidence}</span>
                  <p style={{color: 'var(--dim)', fontSize: 11.5, margin: '6px 0 10px'}}>
                    {t.evidenceHint}
                  </p>
                  {a.hvdc_evidence.map((ev, i) => (
                    <div key={i} style={{
                      borderTop: i ? '1px solid var(--grat-1)' : 0,
                      padding: i ? '9px 0 0' : 0, marginTop: i ? 9 : 0,
                    }}>
                      <div className="num" style={{fontSize: 11, color: 'var(--brass)', letterSpacing: '.04em'}}>
                        {ev.category} · {ev.subtype}
                        <span style={{color: 'var(--dim)'}}>
                          {' '}— {ev.actor}{ev.target ? ` → ${ev.target}` : ''}
                        </span>
                      </div>
                      <div style={{fontSize: 13.5, lineHeight: 1.55, color: 'var(--parchment)', margin: '3px 0'}}>
                        «{ev.evidence}»
                      </div>
                      <div className="num" style={{fontSize: 10.5, color: 'var(--dim)'}}>
                        {ev.source} · confidence {ev.confidence.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </section>
              )}

              {/* Norms — units named, "not enough data" said out loud. */}
              {norms && (
                <section style={{...panelStyle, marginTop: 12}}>
                  <span className="eyebrow" style={{display: 'block', marginBottom: 8}}>{t.norms}</span>
                  <div className="num" style={{fontSize: 12, color: 'var(--muted)', marginBottom: 10}}>
                    {t.genderUsed}: {norms.gender_used} · {t.typicality}:{' '}
                    {typeof norms.overall_typicality === 'number' ? (
                      <span style={{color: 'var(--brass)'}}>{norms.overall_typicality.toFixed(1)}%</span>
                    ) : (
                      <span style={{color: 'var(--dim)'}}>{t.noTypicality}</span>
                    )}
                  </div>
                  {(lang === 'ru' ? norms.typicality_warning_ru : norms.typicality_warning_en) && (
                    <p style={{color: 'var(--notice-ink)', fontSize: 12, lineHeight: 1.5, margin: '0 0 10px'}}>
                      {lang === 'ru' ? norms.typicality_warning_ru : norms.typicality_warning_en}
                    </p>
                  )}
                  {norms.deviations.length > 0 && (
                    <div style={{overflowX: 'auto'}}>
                      <table className="num" style={{width: '100%', borderCollapse: 'collapse',
                        fontFamily: 'var(--font-data)', fontSize: 11.5}}>
                        <thead>
                          <tr style={{color: 'var(--dim)', textAlign: 'left'}}>
                            <th style={thStyle}>{t.indicator}</th>
                            <th style={{...thStyle, textAlign: 'right'}}>{t.yours}</th>
                            <th style={{...thStyle, textAlign: 'right'}}>{t.norm}</th>
                            <th style={{...thStyle, textAlign: 'right'}}>{t.deviation}</th>
                            <th style={{...thStyle, textAlign: 'right'}}>{t.basedOn}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {norms.deviations.map((d, i) => (
                            <tr key={i} style={{borderTop: '1px solid var(--grat-1)'}}>
                              <td style={tdStyle}>
                                {d.indicator}
                                {d.significance === 'significant' && (
                                  <span style={{color: 'var(--brass)'}}> ●</span>
                                )}
                              </td>
                              <td style={{...tdStyle, textAlign: 'right'}}>{d.user_value.toFixed(2)}</td>
                              <td style={{...tdStyle, textAlign: 'right'}}>{d.norm_value.toFixed(2)}</td>
                              <td style={{...tdStyle, textAlign: 'right',
                                color: d.significance === 'significant' ? 'var(--brass)' : 'var(--muted)'}}>
                                {d.deviation > 0 ? '+' : ''}{d.deviation.toFixed(2)}
                                {' '}{d.deviation_unit === 'percentage_points' ? t.pp : d.deviation_unit}
                              </td>
                              <td style={{...tdStyle, textAlign: 'right', color: 'var(--dim)'}}>
                                {d.events_observed}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {(lang === 'ru' ? norms.method_note_ru : norms.method_note_en) && (
                    <p style={{color: 'var(--dim)', fontSize: 11.5, lineHeight: 1.5, marginTop: 10}}>
                      {lang === 'ru' ? norms.method_note_ru : norms.method_note_en}
                    </p>
                  )}
                </section>
              )}

              {/* Interpretation — last, and labelled. */}
              {a.interpretation && (
                <section style={{...panelStyle, marginTop: 12}}>
                  <span className="eyebrow" style={{display: 'block', marginBottom: 8}}>{t.interpretation}</span>
                  {a.interpretation.split('\n').filter(Boolean).map((line, i) => (
                    <p key={i} style={{fontSize: 14, lineHeight: 1.62, color: 'var(--parchment)', margin: '0 0 9px'}}>
                      {line}
                    </p>
                  ))}
                  <p style={{color: 'var(--dim)', fontSize: 11.5, margin: '4px 0 0'}}>
                    {t.interpretationNote}
                  </p>
                </section>
              )}

              {a.recommendations.length > 0 && (
                <section style={{...panelStyle, marginTop: 12}}>
                  <span className="eyebrow" style={{display: 'block', marginBottom: 8}}>{t.recommendations}</span>
                  <ul style={{margin: 0, paddingLeft: 18, color: 'var(--parchment)', fontSize: 13.5, lineHeight: 1.6}}>
                    {a.recommendations.map((r, i) => <li key={i} style={{marginBottom: 4}}>{r}</li>)}
                  </ul>
                </section>
              )}
            </div>

            {/* ── instrument panel ── */}
            <div>
              <div className="panel">
                {ca && (
                  <>
                    <PanelTable title={t.characters}>
                      <Row label={t.male} value={ca.male_characters} />
                      <Row label={t.female} value={ca.female_characters} />
                      <Row label={t.animal} value={ca.animal_characters} />
                    </PanelTable>
                    <PanelTable title={t.interactions}>
                      <Row label={t.friendly} value={ca.friendly_interactions} />
                      <Row label={t.aggressive} value={ca.aggressive_interactions} />
                      <Row label={t.sexual} value={ca.sexual_interactions} />
                    </PanelTable>
                    <PanelTable title={t.outcomes}>
                      <Row label={t.successes} value={ca.successes} />
                      <Row label={t.failures} value={ca.failures} />
                      <Row label={t.goodFortunes} value={ca.good_fortunes} />
                      <Row label={t.misfortunes} value={ca.misfortunes} />
                    </PanelTable>
                    <PanelTable title={t.emotions}>
                      <Row label={t.positive} value={ca.positive_emotions} />
                      <Row label={t.negative} value={ca.negative_emotions} />
                    </PanelTable>
                  </>
                )}

                {a.symbols.length > 0 && (
                  <div className="panel-block">
                    <span className="eyebrow" style={{display: 'block', marginBottom: 9}}>{t.symbols}</span>
                    {a.symbols.slice(0, 8).map((s, i) => (
                      <div key={i} style={{marginBottom: 9}}>
                        <div className="num" style={{fontSize: 11.5, color: 'var(--brass)'}}>
                          {s.symbol}
                          {s.archetype && <span style={{color: 'var(--dim)'}}> · {s.archetype}</span>}
                        </div>
                        <div style={{fontSize: 12.5, lineHeight: 1.5, color: 'var(--muted)'}}>
                          {lang === 'ru' ? s.interpretation_ru : s.interpretation_en}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {a.lunar_context && (
                  <PanelTable title={t.lunar}>
                    <Row label={t.lunarDay} value={a.lunar_context.lunar_day} />
                    <tr>
                      <td>{t.phase}</td>
                      <td style={rCell}>{a.lunar_context.lunar_phase}</td>
                    </tr>
                    {a.lunar_context.moon_sign && (
                      <tr>
                        <td>{t.moonSign}</td>
                        <td style={rCell}>{a.lunar_context.moon_sign}</td>
                      </tr>
                    )}
                  </PanelTable>
                )}

                {(a.themes.length > 0 || a.archetypes.length > 0) && (
                  <div className="panel-block">
                    {a.themes.length > 0 && (
                      <>
                        <span className="eyebrow" style={{display: 'block', marginBottom: 7}}>{t.themes}</span>
                        <div style={{fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 10}}>
                          {a.themes.join(' · ')}
                        </div>
                      </>
                    )}
                    {a.archetypes.length > 0 && (
                      <>
                        <span className="eyebrow" style={{display: 'block', marginBottom: 7}}>{t.archetypes}</span>
                        <div style={{fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.6}}>
                          {a.archetypes.map((x) => x.replace(/_/g, ' ')).join(' · ')}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Disclaimer as normal text next to the result, not footer fine print. */}
          <p style={{color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.55, marginTop: 14, maxWidth: '66ch'}}>
            <b style={{color: 'var(--parchment)', fontWeight: 500}}>{t.disclaimerLead}</b>{' '}
            {a.disclaimer || t.disclaimerFallback}
          </p>

          {/* Provenance strip — proof of which coder produced these numbers. */}
          <div className="provenance" style={{display: 'flex', flexWrap: 'wrap', gap: '4px 18px'}}>
            {a.hvdc_coder_version && (
              <span><b style={provLabel}>{t.provCoder}</b> {a.hvdc_coder_version}</span>
            )}
            <span><b style={provLabel}>{t.provMethod}</b> {a.methodology}</span>
            {a.dream_id && <span><b style={provLabel}>{t.provId}</b> {a.dream_id}</span>}
            {a.analyzed_at && <span><b style={provLabel}>{t.provAt}</b> {a.analyzed_at}</span>}
          </div>
        </>
      )}
    </main>
  );
}

// ── presentational helpers ──────────────────────────────────────────────────
const panelStyle: React.CSSProperties = {
  border: '1px solid var(--grat-2)', background: 'var(--shelf)', padding: '13px 15px',
};
const labelStyle: React.CSSProperties = {
  display: 'block', color: 'var(--dim)', fontFamily: 'var(--font-data)', fontSize: 10,
  letterSpacing: '.04em', textTransform: 'uppercase', margin: '0 0 3px',
};
const inputStyle: React.CSSProperties = {
  width: '100%', background: 'var(--abyss)', color: 'var(--parchment)',
  border: '1px solid var(--grat-2)', fontFamily: 'var(--font-data)', fontSize: 12, padding: '6px 8px',
};
const rCell: React.CSSProperties = { textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--muted)' };
const thStyle: React.CSSProperties = { padding: '0 6px 6px 0', fontWeight: 400 };
const tdStyle: React.CSSProperties = { padding: '5px 6px 5px 0', color: 'var(--parchment)' };
const provLabel: React.CSSProperties = { color: 'var(--muted)', fontWeight: 400 };

function PanelTable({title, children}: {title: string; children: React.ReactNode}) {
  return (
    <div className="panel-block">
      <span className="eyebrow" style={{display: 'block', marginBottom: 9}}>{title}</span>
      <table className="num" style={{width: '100%', borderCollapse: 'collapse',
        fontFamily: 'var(--font-data)', fontSize: 12}}>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function Row({label, value}: {label: string; value: number}) {
  return (
    <tr>
      <td style={{color: 'var(--parchment)'}}>{label}</td>
      <td style={{...rCell, color: value > 0 ? 'var(--brass)' : 'var(--dim)'}}>{value}</td>
    </tr>
  );
}
