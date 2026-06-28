# {FEATURE} — Requirements

> **English TL;DR:** Why this feature exists, who it's for, what
> success looks like. Written BEFORE any code. Uses EARS-style
> acceptance criteria. Names of files/classes/tables are NOT
> specified here — agent derives them from repo conventions.

**Feature name:** {short slug}
**Owner:** {who decides scope}
**Status:** draft | accepted | implemented | abandoned
**Created:** YYYY-MM-DD
**Related ADR:** ADR-NNN (link in `soul.md §6` if applicable)

---

## §1 Problem statement

What user-visible problem does this solve? Why now? What happens if
we DON'T build it?

(1-3 paragraphs, plain language. Avoid astrology jargon if the user
isn't an astrologer.)

## §2 Out of scope

What this feature explicitly does NOT do. Critical for keeping scope
honest.

## §3 Users and use cases

- **Primary user:** {persona} — {what they want}
- **Secondary user:** {persona} — {what they want}
- **Use case 1:** When ... they ... so that ...
- **Use case 2:** ...

## §4 Acceptance criteria (EARS)

EARS = Easy Approach to Requirements Syntax. Format:
> **WHEN** \<trigger\>, the system **SHALL** \<behavior\>.
> **WHILE** \<state\>, the system **SHALL** \<continuous behavior\>.
> **IF** \<exception\>, **THEN** the system **SHALL** \<recovery\>.

### Required
- WHEN ..., the system SHALL ...
- WHEN ..., the system SHALL ...

### Domain-specific (per `docs/steering/domain.md` rules)
- Every interpretive response SHALL include a disclaimer
  (`has_disclaimer()` returns True).
- Every interpretive claim SHALL carry provenance (source citation).
- Every astronomical computation SHALL be deterministic
  (no LLM in the computation path).
- Acceptance does NOT bind to **exact text** of interpretive output —
  output text is variable; structural / provenance / tone criteria bind.

## §5 Non-functional requirements

- **Performance:** ...
- **Cost (LLM tokens):** ...
- **Privacy:** ...
- **Localization:** which of ru/en/de/es/fr.

## §6 Open questions

- [ ] {question for owner}
- [ ] {question for owner}

## §7 Decided trade-offs

- Chose X over Y because ...
- Deferred Z to a follow-up because ...
