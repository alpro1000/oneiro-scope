---
name: research-symbol
description: Research a new dream symbol and propose an entry for backend/services/dreams/knowledge_base/symbols.json — Hall/Van de Castle category, Jungian archetype link, bilingual interpretation. Use when the user asks to "add a dream symbol", "research <word> for dream KB", or invokes /research-symbol <word>.
---

# /research-symbol — Add a new dream symbol

## What this does

Helps the owner expand the dream knowledge base in a methodologically
consistent way. The KB currently holds 56 symbols. New entries must:

1. Map to a Hall/Van de Castle category from `list_hvdc_categories`.
2. (Optional but encouraged) Link to a Jungian archetype from
   `list_archetypes`.
3. Provide bilingual interpretation (ru + en), 1–3 sentences each.
4. Avoid the prohibited content list (fortune-telling, curses, medical
   diagnosis — see `docs/steering/product.md`).

## How to invoke

- "/research-symbol surveillance"
- "Add new dream symbol: 'algorithm'"

## Workflow

1. Call `mcp__oneiro__list_hvdc_categories` and `list_archetypes` to
   ground the available taxonomy.
2. Look up the symbol in modern dream-research literature briefly
   (single web fetch if `WebFetch` is allowed; otherwise rely on prior
   knowledge).
3. Propose an entry as a JSON snippet that matches the existing schema
   in `backend/services/dreams/knowledge_base/symbols.json`.
4. Show the diff (where it would be inserted) and ask for owner
   confirmation before writing.
5. On confirmation, edit `symbols.json`, run
   `pytest backend/tests/test_dream_interpreter_narrative.py` to make
   sure nothing regressed, and commit on the active branch.

## Required input

- **symbol** — the word/concept to add (English form preferred for the
  `symbol` field; interpretations are bilingual).

## Behavior

- Never overwrite an existing symbol without explicit confirmation —
  surface the existing entry first.
- Refuse symbols that fall into the prohibited list.
- After adding, mention the new symbol count and remind the owner that
  the change is on the current branch (not yet pushed).
