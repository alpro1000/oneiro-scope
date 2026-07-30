---
name: design-system
description: Use for ANY frontend or UI work in OneiroScope — building or changing pages, components, charts, wheels, maps, tables, forms, pricing, dashboard. Trigger on "вёрстка", "компонент", "страница", "экран", "дизайн", "стили", "Tailwind", "CSS", "колесо", "график", "таблица", React/Next.js UI, or whenever visual output is produced. Carries the design tokens, type roles, and the mandatory data-display rules that differentiate the product from competitors.
---

# OneiroScope design system

## Reference implementation
`astrocartography.html` in the repo root is the canonical example. Read it before building any new screen. It establishes projection, panel layout, hover readout, legend toggles, provenance strip. **Do not redesign it.** Match it.

## Position
**Instrument, not divination.** The product sells a verifiable calculation: ephemeris with provenance, orbs, arc-second accuracy. Interpretation is done by the host model or the user. The visual language must read as a measuring instrument.

References: nautical charts, engraved 19th-century astronomical atlases, brass instruments, ephemeris tables.

## Mandatory data rules — non-negotiable

Co-Star, the market leader, is also monochrome and monospaced. **Styling does not differentiate us — data does.** Their natal wheel shows no degrees, no orbs, no house system, no ephemeris version, no timezone. Monospace there is decoration.

Every screen showing a calculation MUST display:

1. **Positions with degrees and arcminutes**, not just the sign. `Рак 9°50′`, not `Cancer`.
2. **Aspects with orb and applying/separating.** `Opposition, orb 9.42°, separating`.
3. **Borderline placements flagged explicitly** when within 1° of a cusp — never silently asserted.
4. **Timezone and historical offset shown** for the birth moment. `UTC+3 (Europe/Kyiv, 1977)`.
5. **Provenance strip** at the bottom: engine, ephemeris version, house system, `request_id`.

This is not fine print. If a design proposal removes any of it for compositional cleanliness, reject the proposal. Removing it makes the product a styling clone of a competitor with a far bigger budget.

Astrocartography is not offered by Co-Star at all — it is our strongest uncovered module and deserves prominence.

## Tokens
Import `frontend/styles/tokens.css`. Never hardcode a hex value in a component.

```
--abyss #071320   background, deep water
--shelf #0C1E2E   containers
--panel #0A1B29   instrument panels
--land  #152C3E   landmass fill
--grat1 #1B3549   grid, dividers
--grat2 #22415A   borders

--parchment #E7DDC7  primary text
--muted     #89A0B1  secondary
--dim       #5C7385  axis labels, captions

--brass     #D2A64B  the only accent
--brassDim  #8A6E32  eyebrows, service labels
```

**One accent colour only.** No second accent. Emphasis comes from brass or from parchment brightness, never from a new hue.

Planet colours are the only permitted chromatic set, derived from classical metals:
```
Sun #E8C25A · Moon #C7D3DD · Mercury #9FD5C8 · Venus #DB8F6C · Mars #C6544B
Jupiter #B9A8DA · Saturn #8493A2 · Uranus #6FBACB · Neptune #5F84BC · Pluto #997280
```

## Type — three faces, fixed roles

| Role | Face | Where |
|---|---|---|
| Display | **Bodoni Moda** | h1–h2, place names. Italic for accent within a heading |
| UI | **Instrument Sans** | buttons, prose, labels, nav |
| Data | **IBM Plex Mono** | degrees, coordinates, orbs, times, versions, eyebrows |

**Every number and every measurement is set in mono.** This is the strongest single differentiator — it signals "calculation, not opinion". Never set a degree value in the UI face.

Eyebrow: mono, 10.5px, `letter-spacing:.22em`, uppercase, `--brassDim`.
Headings: `letter-spacing:-.015em`, `line-height:.94`.

## Form
- `border-radius: 0` everywhere. Instruments and charts are not rounded.
- **Borders, not shadows.** 1px `--grat2`. No `box-shadow`, no glow.
- Dashes carry meaning, never decoration: solid = MC and Asc, dashed = IC and Desc, dotted = cursor crosshair.
- Stroke widths 0.7–1.4px; active highlight up to 2.4px.

## Layout pattern
Data area plus instrument panel:
```
grid-template-columns: minmax(0,1fr) 300px;   /* collapses to 1fr below 900px */
```
Panel is a stack of blocks separated by 1px `--grat1`, each with a mono eyebrow label.

## Voice
- Short headings, no exaltation. "Где что звучит" yes; "Раскройте тайну судьбы" no.
- Never round numbers in a flattering direction. `0.63°`, not "почти точно".
- Separate the verifiable from the traditional. Geometry is checkable; interpretation is a tradition. Say it plainly, not in a footnote.
- Disclaimer as normal text next to the result, not 8px grey in the footer.
- Russian without bureaucratese and without esoteric jargon.

## Borrowed pattern worth using
Co-Star's form is a sentence with blanks — «Я родился в ___ ___ в ___» — no labels, no field boxes. Better than three stacked labels and fits the editorial register. Use it for birth-data entry.

Unlike Co-Star, **do not gate the result behind an email.** Free tier is one chart for life; a barrier before the first result kills conversion. Email is requested when quota is exhausted or a PDF is wanted.

## Checklist before shipping a screen
- Numbers in mono?
- Degrees, orbs, applying/separating present?
- Borderline placements flagged?
- Timezone and historical offset shown?
- Provenance strip present?
- `border-radius: 0`, no shadows?
- Brass the only accent?
- Works at 380px?
- `prefers-reduced-motion` honoured?
- Shows numbers a competitor does not?
