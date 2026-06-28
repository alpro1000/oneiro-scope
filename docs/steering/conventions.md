# conventions.md — How we work

> English TL;DR: how we work — mantra, anti-bloat rules, task-writing
> rules, doc-update matrix, communication.

Adopted from peer-review scaffold (2026-06-28).

## §1 Мантра

> «Сначала читаешь весь репо. Потом определяешь naming. Потом пишешь.»

## §2 Karpathy rules (анти-bloat)

- Можно 50 строк вместо 200 — пиши 50.
- Не трогай код, не связанный с задачей.
- Не добавляй «гибкость» и «конфигурируемость», о которых не просили.
- Не уверен — спроси, не угадывай молча.
- Определи критерии успеха ДО кода, потом итерируй к ним.
- Не пиши «error handling» для сценариев, которые не могут случиться.
- Не пиши «backwards compatibility» если можно просто поменять код.
- Не пиши комментарии про ОЧЕВИДНОЕ. Комментируй WHY, не WHAT.

## §3 Commits & branches

**Commits** (используются prefix'ы, но в проекте уже устоялся стиль
`feat(...)` через Conventional Commits — продолжаем его):
- `feat(scope):` — новая фича
- `fix(scope):` — баг-фикс
- `refactor(scope):` — реструктуризация без изменения поведения
- `docs(scope):` — только документация
- `test(scope):` — только тесты
- `ci(scope):` — изменения CI/CD
- `chore(scope):` — рутина (deps, version bumps)

**Branches:** `claude/<task-description>-<random5chars>` или
`<topic>/<short-name>` (например `feat/strategic-analyst-pivot`).

## §4 Правила написания task / spec

- ❌ НЕ специфицируй имена переменных, файлов, классов, таблиц.
- ✅ Описывай в терминах **бизнес-логики + архитектуры**; naming агент
  выводит из репо.
- Критерии в **EARS-стиле**: «КОГДА \<условие\>, система ДОЛЖНА
  \<поведение\>».
- Для домена — критерии на **провенанс / дисклеймер / допуск**, не на
  дословный текст.

## §5 Update-матрица context docs

| Когда | Что обновить |
|---|---|
| Новый источник / AI-провайдер / хранилище | `docs/steering/tech.md` |
| Изменение layout репо | `docs/steering/structure.md` |
| Новое доменное правило (орб, символ, традиция, дисклеймер) | `docs/steering/domain.md` |
| Изменение workflow | `docs/steering/conventions.md` (этот файл) |
| Архитектурное решение (ADR) | `docs/soul.md §6` |
| После КАЖДОЙ сессии | `docs/soul.md §9` (session log) |

## §6 Жизненный цикл фичи (SDD — Spec-Driven Development)

1. **Спека:** `docs/specs/{feature}/{requirements,design,tasks}.md`
2. **Реализация** по `tasks.md` (каждая Gate = commit)
3. **По завершении:** `docs/soul.md §9` + `next-session.md` (если есть)

Для маленьких задач (<2 часа работы) — пропускаем `specs/` и идём
прямо в branch + commit.

## §7 Gates дисциплины (повторяю из CLAUDE.md)

1. **Pre-session:** Claude Code читает mandatory block в `CLAUDE.md`
   первым делом. Если не сделал в первые 3 минуты — owner останавливает
   и напоминает.
2. **Post-session:** Claude Code обновляет `docs/soul.md §9`. Это
   **последний Gate каждой задачи**.
3. **Архитектурные решения:** обновляются `docs/steering/{tech,
   structure,domain,product}.md` + добавляется ADR в `soul.md §6`.
4. **Новый проект/корпус:** `soul.md §2.3-§2.4`.
5. **Sync с Project Knowledge на claude.ai:** owner делает раз в неделю.

## §8 Commit & PR безопасность

- НЕ коммитить секреты (`.env`, `*.key`, `credentials.json`).
- НЕ скипать pre-commit hooks (`--no-verify`) без явного запроса owner'а.
- НЕ force-push в `main` / `master`.
- При работе в `claude/*` ветке — push с `-u origin <branch>`,
  PR создавать только когда owner просит.

## §9 Communication style (между сессиями и в PR)

- **Брифинг агенту:** explain цель, что уже сделано/исключено, дать
  путь к файлам и номера строк. **Не делегируй понимание** — не пиши
  «исправь баг based on findings», пиши «строка 142 в file X: orb_deg
  должен быть 8 для conjunction».
- **PR-описание:** короткое summary + test plan чек-листом. Тяжёлый
  диалог — в commit'ах, не в PR body.
- **End-of-turn:** одно-два предложения. Что сделано, что дальше. Без
  декораций.

## §10 Когда задаём вопросы owner'у

- Архитектурный выбор (auth strategy, payment provider, hosting).
- Этический выбор (включение фичи, которая может задеть disclaimer).
- Когда уверенность в решении < 70% и решение трудно откатить.

**НЕ задаём** вопросы, на которые ответ есть в `domain.md` /
`tech.md` / `structure.md` / `soul.md`. Сначала читаем.
