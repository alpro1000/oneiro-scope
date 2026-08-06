/**
 * Dream coding, with the evidence shown — an MCP App view for `analyze_dream`.
 *
 * This is the view that earns the whole approach. Hall/Van de Castle coding is
 * a count of things found in a text, and a count is only worth as much as its
 * provenance: "aggression: 1" is an assertion, "aggression: 1, because of the
 * clause «за мной гналась собака»" is a claim the reader can check against
 * their own dream in one glance.
 *
 * So the dream text is printed with every coded clause marked, and each entry
 * in the ledger points back at the phrase it came from. The confidence order
 * is preserved top to bottom: deterministic coding first (1.0), norms next,
 * symbols after that, and any model prose last and labelled.
 */

import type { ToolResult } from './bridge';
import { markUp, type Evidence } from './clause-marks';
import { ASK_LABEL, askButton, esc, fromResult, mountView, type Lang } from './view';

interface Symbol {
  symbol?: string;
  category?: string;
  archetype?: string;
  significance?: number;
}

interface Payload {
  hvdc_evidence?: Evidence[];
  hvdc_coder_version?: string;
  content_analysis?: Record<string, unknown>;
  symbols?: Symbol[];
  primary_emotion?: string;
  themes?: string[];
  archetypes?: string[];
  norm_comparison?: Record<string, unknown>;
  degraded?: unknown[];
  disclaimer?: string;
  interpretation?: string;
  meta?: Record<string, unknown>;
  locale?: string;
}

const CATEGORY: Record<Lang, Record<string, string>> = {
  ru: {
    aggression: 'агрессия', friendliness: 'дружелюбие', sexuality: 'сексуальность',
    success: 'успех', failure: 'неудача', misfortune: 'несчастье',
    good_fortune: 'удача', characters: 'персонажи', emotions: 'эмоции',
  },
  en: {
    aggression: 'aggression', friendliness: 'friendliness', sexuality: 'sexuality',
    success: 'success', failure: 'failure', misfortune: 'misfortune',
    good_fortune: 'good fortune', characters: 'characters', emotions: 'emotions',
  },
};

const COPY = {
  ru: {
    title: 'Разбор сна',
    eyebrow: 'Hall / Van de Castle · 1966',
    text: 'Текст с отмеченными уликами',
    ledger: 'Что закодировано и почему',
    counts: 'Счётчики',
    symbols: 'Символы',
    emotion: 'Ведущая эмоция',
    themes: 'Темы',
    degraded: 'Что не удалось посчитать',
    interpretation: 'Толкование модели',
    actor: 'кто', target: 'на кого', source: 'правило',
    coder: 'кодировщик',
    noText: 'Текст сна не передан — улики показаны списком.',
    llmNote: 'Ниже — синтез языковой модели (0.7). Всё, что выше, — '
      + 'детерминированный подсчёт (1.0) и словарь (0.8).',
    waiting: 'Ожидание разбора…',
    empty: 'Нет данных. Вызовите analyze_dream.',
    askOne: 'Объясни эту закодированную улику из моего сна',
    askAll: 'Прочитай этот разбор целиком по Холлу/Ван де Каслу',
    askHint: 'Нажмите «объяснить» у любой улики — в чат уйдёт сама фраза и её правило.',
    disclaimerLead: 'Подсчёт проверяем: под каждым числом лежит фраза.',
    disclaimer: 'Значение символа — традиция толкования, не диагноз. '
      + 'Рефлексивно-развлекательный материал, не медицинский, психологический, '
      + 'юридический или финансовый совет.',
  },
  en: {
    title: 'Dream coding',
    eyebrow: 'Hall / Van de Castle · 1966',
    text: 'Text with the coded clauses marked',
    ledger: 'What was coded, and why',
    counts: 'Counts',
    symbols: 'Symbols',
    emotion: 'Leading emotion',
    themes: 'Themes',
    degraded: 'What could not be computed',
    interpretation: 'Model interpretation',
    actor: 'actor', target: 'target', source: 'rule',
    coder: 'coder',
    noText: 'The dream text was not returned — the evidence is listed instead.',
    llmNote: 'Below is language-model synthesis (0.7). Everything above is '
      + 'deterministic coding (1.0) and the symbol dictionary (0.8).',
    waiting: 'Waiting for the analysis…',
    empty: 'No data. Call analyze_dream.',
    askOne: 'Explain this coded piece of evidence from my dream',
    askAll: 'Read this Hall/Van de Castle coding as a whole',
    askHint: 'Press "explain" on any item — the clause and its rule go to the chat.',
    disclaimerLead: 'The coding is checkable: every number has a clause under it.',
    disclaimer: 'What a symbol means is a tradition of interpretation, not a '
      + 'diagnosis. Reflective / entertainment material, not medical, '
      + 'psychological, legal or financial advice.',
  },
} as const;

function countRows(counts: Record<string, unknown>, lang: Lang): string {
  return Object.entries(counts)
    .filter(([, v]) => typeof v === 'number')
    .map(([k, v]) => `<div class="kv"><span>${CATEGORY[lang][k] ?? esc(k)}</span>`
      + `<b class="num">${v as number}</b></div>`)
    .join('');
}

function render(payload: Payload, lang: Lang, args: Record<string, unknown>): string {
  const t = COPY[lang];
  const evidence = payload.hvdc_evidence ?? [];
  // The dream text comes from the tool's ARGUMENTS, not its response: the
  // server deliberately does not echo the text back, and the host already has
  // it. Nothing is round-tripped that the user just typed.
  const text = typeof args.dream_text === 'string' ? args.dream_text : '';

  const ledger = evidence.map((e, i) => `<div class="ev-row">
      <div class="ev-head">
        <span class="ev-n num">${i + 1}</span>
        <span class="ev-cat">${CATEGORY[lang][e.category ?? ''] ?? esc(e.category ?? '')}</span>
        ${e.subtype ? `<span class="dim">· ${esc(e.subtype)}</span>` : ''}
        <span class="num ev-conf">${(e.confidence ?? 1).toFixed(1)}</span>
      </div>
      ${e.evidence ? `<div class="ev-quote">«${esc(e.evidence)}»</div>` : ''}
      <div class="ev-meta dim">
        ${e.actor ? `${t.actor}: ${esc(e.actor)}` : ''}
        ${e.target ? ` · ${t.target}: ${esc(e.target)}` : ''}
      </div>
      ${e.source ? `<div class="ev-src dim">${t.source}: ${esc(e.source)}</div>` : ''}
      ${askButton(
        `${t.askOne}: ${e.category ?? ''}${e.subtype ? ` / ${e.subtype}` : ''}, `
        + `«${e.evidence ?? ''}»${e.actor ? `, ${t.actor}: ${e.actor}` : ''}`
        + `${e.target ? `, ${t.target}: ${e.target}` : ''}. ${e.source ?? ''}`,
        ASK_LABEL[lang],
      )}
    </div>`).join('');

  const symbols = (payload.symbols ?? []).map((s) =>
    `<div class="kv"><span>${esc(s.symbol ?? '')}</span>`
    + `<b class="dim">${esc(s.category ?? '')}${s.archetype ? ` · ${esc(s.archetype)}` : ''}</b></div>`
  ).join('');

  const degraded = (payload.degraded ?? []).map((d) =>
    `<li>${esc(typeof d === 'string' ? d : JSON.stringify(d))}</li>`).join('');

  const meta = payload.meta ?? {};
  const provBits = [
    payload.hvdc_coder_version
      ? `<span><b>${t.coder}</b> ${esc(payload.hvdc_coder_version)}</span>` : '',
    meta.request_id ? `<span><b>request</b> ${esc(String(meta.request_id))}</span>` : '',
  ].filter(Boolean).join('');

  return `
    <div class="head">
      <div class="eyebrow">${t.eyebrow}</div>
      <h1>${t.title}</h1>
    </div>
    <div class="wrap">
      <div>
        <section>
          <div class="eyebrow">${t.text}</div>
          ${text
            ? `<p class="dream">${markUp(text, evidence)}</p>`
            : `<p class="note">${t.noText}</p>`}
        </section>
        <section>
          <div class="eyebrow">${t.ledger}</div>
          ${ledger || `<p class="dim">—</p>`}
          ${evidence.length ? `${askButton(
            `${t.askAll}. ${JSON.stringify(payload.content_analysis ?? {})}`,
            t.askAll, true,
          )}<p class="ask-hint">${t.askHint}</p>` : ''}
        </section>
      </div>
      <div class="panels">
        ${payload.content_analysis ? `<section>
          <div class="eyebrow">${t.counts}</div>
          ${countRows(payload.content_analysis, lang)}
        </section>` : ''}
        ${payload.primary_emotion ? `<section>
          <div class="eyebrow">${t.emotion}</div>
          <div class="kv"><span>${esc(payload.primary_emotion)}</span></div>
        </section>` : ''}
        ${symbols ? `<section>
          <div class="eyebrow">${t.symbols}</div>${symbols}
        </section>` : ''}
        ${degraded ? `<section>
          <div class="eyebrow">${t.degraded}</div>
          <ul class="deg">${degraded}</ul>
        </section>` : ''}
      </div>
    </div>
    ${payload.interpretation ? `<section class="llm">
      <div class="eyebrow">${t.interpretation}</div>
      <p class="note">${t.llmNote}</p>
      <p class="prose">${esc(payload.interpretation)}</p>
    </section>` : ''}
    <div class="prov">${provBits}</div>
    <p class="disclaimer"><b>${t.disclaimerLead}</b> ${esc(payload.disclaimer ?? t.disclaimer)}</p>
  `;
}

mountView<Payload>({
  pick: (result: ToolResult) =>
    fromResult<Payload>(result, (c) =>
      Array.isArray((c as Payload).hvdc_evidence) ? (c as Payload) : null),
  render,
  strings: {
    ru: { waiting: COPY.ru.waiting, empty: COPY.ru.empty },
    en: { waiting: COPY.en.waiting, empty: COPY.en.empty },
  },
});
