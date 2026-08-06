/**
 * How to connect OneiroScope to a chat app.
 *
 * The connector is the primary way the product is used — the web screens are
 * the instrument, the connector is the whole service inside Claude / ChatGPT /
 * Gemini. Until now that instruction existed only on the backend portal, at a
 * different host from the app people actually open, so nothing in the Next
 * navigation ever explained how to get it.
 *
 * Server Component: this is static text plus one URL from the environment.
 * The only client piece is the copy button.
 */

import type { Metadata } from 'next';
import Link from 'next/link';
import CopyField from '@/components/CopyField';

export const metadata: Metadata = {
  title: 'Подключение · Connect',
  description: 'Add OneiroScope to Claude, ChatGPT or Gemini as an MCP connector.',
};

type Lang = 'ru' | 'en';

/** Derived from the backend base URL — the MCP surface is mounted on it. */
function connectorUrl(): string {
  const base = process.env.NEXT_PUBLIC_MCP_URL
    || (process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '')}/mcp` : '');
  return base;
}

const COPY = {
  ru: {
    eyebrow: 'подключение · mcp',
    titleA: 'Один адрес — ', titleEm: 'три', titleB: ' чата',
    lede: 'OneiroScope подключается как MCP-коннектор. Устанавливать нечего: '
      + 'вы вставляете один адрес в настройки своего чата, и инструменты '
      + 'появляются прямо в диалоге.',
    urlLabel: 'Адрес коннектора',
    copy: 'скопировать', copied: 'скопировано',
    urlMissing: 'адрес появится после настройки NEXT_PUBLIC_API_URL',
    claude: 'Claude',
    claudeSteps: [
      'Настройки → Connectors → «Add custom connector».',
      'Вставьте адрес выше и пройдите вход.',
      'Готово — инструменты появятся в чате.',
    ],
    claudeNote: 'Пользовательские коннекторы доступны на платных планах; '
      + 'администратор организации может их ограничить.',
    gpt: 'ChatGPT',
    gptSteps: [
      'Настройки → «Безопасность и вход» → включите режим разработчика.',
      'Настройки → «Плагины» (или chatgpt.com/plugins) → «+».',
      'Вставьте адрес выше.',
    ],
    gptNote: 'Нужен Plus / Pro / Business — на бесплатном тарифе '
      + 'пользовательских коннекторов нет.',
    gem: 'Gemini',
    gemSteps: [
      'Откройте gemini.google.com/apps.',
      'Внизу добавьте ссылку на пользовательское приложение — вставьте адрес выше.',
    ],
    gemNote: 'Поддержка MCP в Gemini разворачивается постепенно.',
    firstTitle: 'Первый вопрос',
    firstBody: 'Просто напишите свои данные рождения в чат — сервис сам '
      + 'предложит порядок разбора.',
    firstExample: 'Посчитай мою карту: 12 марта 1990, 14:30, Прага',
    firstNote: 'Дальше спрашивайте свободно: деньги, призвание, ближайшее '
      + 'десятилетие, города, лучший день для разговора — или расскажите сон.',
    troubleTitle: 'Если что-то не так',
    trouble: [
      ['Ошибка 401', 'коннектор просит вход — завершите его в окне чата.'],
      ['Первый ответ долгий', 'сервер просыпается из простоя; спросите ещё раз.'],
      ['В ChatGPT нет кнопки', 'включите режим разработчика; на бесплатном тарифе коннекторов нет.'],
      ['Пропали инструменты', 'чат кэширует их список — переподключите коннектор.'],
    ],
    diagTitle: 'Самопроверка',
    diagBody: 'Страница диагностики называет, что именно настроено неверно на сервере.',
    diagLink: 'Открыть диагностику',
    webTitle: 'А без чата?',
    webBody: 'Расчётные экраны работают здесь и без коннектора:',
    webNatal: 'натальная карта', webAcg: 'астрокартография',
    webCal: 'лунный календарь', webDreams: 'разбор снов',
    disclaimerLead: 'Расчёты — астрономия, они проверяемы.',
    disclaimer: 'Толкования — традиция, а не прогноз. Материал '
      + 'рефлексивно-развлекательный: не медицинский, психологический, '
      + 'юридический или финансовый совет.',
  },
  en: {
    eyebrow: 'connect · mcp',
    titleA: 'One URL, ', titleEm: 'three', titleB: ' chats',
    lede: 'OneiroScope connects as an MCP connector. Nothing to install: paste '
      + 'one URL into your chat app\'s settings and the tools appear in the '
      + 'conversation.',
    urlLabel: 'Connector URL',
    copy: 'copy', copied: 'copied',
    urlMissing: 'the URL appears once NEXT_PUBLIC_API_URL is configured',
    claude: 'Claude',
    claudeSteps: [
      'Settings → Connectors → "Add custom connector".',
      'Paste the URL above and complete the sign-in.',
      'Done — the tools appear in your chat.',
    ],
    claudeNote: 'Custom connectors are a paid-plan feature; organisation '
      + 'admins may restrict them.',
    gpt: 'ChatGPT',
    gptSteps: [
      'Settings → "Security and login" → enable Developer mode.',
      'Settings → "Plugins" (or chatgpt.com/plugins) → "+".',
      'Paste the URL above.',
    ],
    gptNote: 'Requires Plus / Pro / Business — custom connectors are not '
      + 'available on the free tier.',
    gem: 'Gemini',
    gemSteps: [
      'Open gemini.google.com/apps.',
      'At the bottom, add a custom app link — paste the URL above.',
    ],
    gemNote: 'MCP support in Gemini is rolling out gradually.',
    firstTitle: 'Your first question',
    firstBody: 'Just type your birth data in the chat — the service proposes '
      + 'the reading order itself.',
    firstExample: 'Compute my chart: 12 March 1990, 14:30, Prague',
    firstNote: 'From there ask freely: money, vocation, the decade ahead, '
      + 'cities, the best day for a conversation — or describe a dream.',
    troubleTitle: 'If something goes wrong',
    trouble: [
      ['401 error', 'the connector needs sign-in — complete it in the chat window.'],
      ['First response is slow', 'the server wakes from idle; just ask again.'],
      ['No button in ChatGPT', 'enable Developer mode; custom connectors are not on the free plan.'],
      ['Tools disappeared', 'the chat caches the tool list — reconnect the connector.'],
    ],
    diagTitle: 'Self-check',
    diagBody: 'The diagnostics page names exactly what is misconfigured on the server.',
    diagLink: 'Open diagnostics',
    webTitle: 'Without a chat app?',
    webBody: 'The instrument screens work here without the connector:',
    webNatal: 'natal chart', webAcg: 'astrocartography',
    webCal: 'lunar calendar', webDreams: 'dream analysis',
    disclaimerLead: 'The computations are astronomy — verifiable.',
    disclaimer: 'Interpretations are a tradition, not a prediction. This is '
      + 'reflective / entertainment material: not medical, psychological, '
      + 'legal or financial advice.',
  },
} as const;

export default function ConnectPage({ params }: { params: { locale: string } }) {
  const lang: Lang = params.locale === 'ru' ? 'ru' : 'en';
  const t = COPY[lang];
  const url = connectorUrl();
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || '';

  return (
    <main style={{ padding: 'clamp(14px,2.2vw,30px)', maxWidth: '78ch' }}>
      <header style={{ paddingBottom: 14, marginBottom: 22, borderBottom: '1px solid var(--grat-1)' }}>
        <div className="eyebrow">{t.eyebrow}</div>
        <h1 style={{
          fontFamily: 'var(--font-display)', fontSize: 'clamp(28px,4.4vw,44px)',
          letterSpacing: '-.015em', lineHeight: .94, margin: '8px 0 0', fontWeight: 400,
        }}>
          {t.titleA}<em style={{ color: 'var(--brass)' }}>{t.titleEm}</em>{t.titleB}
        </h1>
        <p style={{ color: 'var(--muted)', fontSize: 14, lineHeight: 1.65, margin: '13px 0 0', maxWidth: '62ch' }}>
          {t.lede}
        </p>
      </header>

      <section style={{ marginBottom: 30 }}>
        <div className="eyebrow" style={{ marginBottom: 8 }}>{t.urlLabel}</div>
        <CopyField value={url} copyLabel={t.copy} copiedLabel={t.copied} unavailable={t.urlMissing} />
      </section>

      <div style={{
        display: 'grid', gap: 1, background: 'var(--grat-1)',
        gridTemplateColumns: 'repeat(auto-fit,minmax(230px,1fr))', marginBottom: 30,
      }}>
        <Host name={t.claude} steps={t.claudeSteps} note={t.claudeNote} />
        <Host name={t.gpt} steps={t.gptSteps} note={t.gptNote} />
        <Host name={t.gem} steps={t.gemSteps} note={t.gemNote} />
      </div>

      <Section title={t.firstTitle}>
        <p className="connect-p">{t.firstBody}</p>
        <p className="connect-example">{t.firstExample}</p>
        <p className="connect-p">{t.firstNote}</p>
      </Section>

      <Section title={t.troubleTitle}>
        <dl className="connect-dl">
          {t.trouble.map(([h, b]) => (
            <div key={h}>
              <dt>{h}</dt>
              <dd>{b}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section title={t.diagTitle}>
        <p className="connect-p">{t.diagBody}</p>
        {base && (
          <a className="connect-link" href={`${base}/connect/diagnostics`} target="_blank" rel="noopener noreferrer">
            {t.diagLink} →
          </a>
        )}
      </Section>

      <Section title={t.webTitle}>
        <p className="connect-p">{t.webBody}</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 8 }}>
          <Link className="city-chip" href={`/${lang}/natal`}>{t.webNatal}</Link>
          <Link className="city-chip" href={`/${lang}/astrocartography`}>{t.webAcg}</Link>
          <Link className="city-chip" href={`/${lang}/calendar`}>{t.webCal}</Link>
          <Link className="city-chip" href={`/${lang}/dreams`}>{t.webDreams}</Link>
        </div>
      </Section>

      <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, marginTop: 26, maxWidth: '64ch' }}>
        <b style={{ color: 'var(--parchment)', fontWeight: 500 }}>{t.disclaimerLead}</b> {t.disclaimer}
      </p>
    </main>
  );
}

function Host({ name, steps, note }: { name: string; steps: readonly string[]; note: string }) {
  return (
    <div style={{ background: 'var(--shelf)', padding: '15px 16px 17px' }}>
      <h2 style={{
        fontFamily: 'var(--font-display)', fontSize: 19, fontWeight: 400,
        letterSpacing: '-.015em', margin: '0 0 10px',
      }}>{name}</h2>
      <ol className="connect-ol">
        {steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
      <p className="connect-note">{note}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ paddingTop: 18, marginBottom: 18, borderTop: '1px solid var(--grat-1)' }}>
      <h2 style={{
        fontFamily: 'var(--font-display)', fontSize: 21, fontWeight: 400,
        letterSpacing: '-.015em', margin: '0 0 10px',
      }}>{title}</h2>
      {children}
    </section>
  );
}
