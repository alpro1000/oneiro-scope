# photo-max-extraction — Design

> **English TL;DR:** A frame-set aggregation layer on top of the
> existing deterministic pipeline, plus an explicit coverage/
> degradation map. The guided scanner is a frontend follow-up that
> reuses the same gates client-side.

**Status:** core implemented 2026-07-05 (aggregation + coverage);
scanner = follow-up task.

## Architecture

```
photo set ──► detection ladder (native → 2x/3x upscale → face-crop zoom)
       │            │ reject: yaw gate / no face (reason recorded)
       ▼            ▼
  per-frame FaceMetrics (deterministic, 1.0)
       │
       ▼
  aggregation: per-metric medians + spread (stability),
  per-topic support = share of frames whose own readings
  contain the topic
       │
       ▼
  median profile → PhysiognomyService (KB readings, 0.6)
       │
       ▼
  coverage map: measured / questionnaire-only / guided-scan-only /
  unreadable-in-principle (reasons cited)
```

## Key decisions

1. **Median over mean** — archives contain expression outliers
   (smiles, open mouths); median is the stable face. Same choice as
   `longitudinal.py`.
2. **`support` is a fact, not a confidence change.** Interpretation
   stays 0.6 (tradition tier); support (e.g. 12/12 frames) is a
   1.0-tier measurement about agreement and is reported alongside.
3. **Color/texture normalization rejected** for uncontrolled photos:
   within-frame reference-zone normalization still left ×26 spread and
   failed the child-skin control (2026-07-05). Normalizing sizes is
   already free — every metric is a ratio.
4. **Coverage classes are static knowledge encoded once:**
   - measured: the FaceMetrics-derived traits;
   - questionnaire-only: eyelid, gaze, brows, ears, cheeks,
     cheekbones (no reliable FaceMesh heuristic);
   - guided-scan-only: shen/gaze steadiness (needs video), palace
     texture (needs controlled even light — maybe);
   - unreadable-in-principle from casual photos: qi-se color, palace
     smoothness (evidence: this spec §requirements, soul.md §9).
5. **Scanner (frontend, follow-up):** browser FaceLandmarker page
   `/[locale]/face` runs the SAME gates live (yaw asymmetry ≤ 0.20,
   inner-lip gap ≤ 6% of mouth width, left/right brightness symmetry)
   and auto-captures frames that pass; landmarks-only leave the
   device (privacy-first), then the same MCP/API aggregation.

## Contracts

`aggregate.analyze_frames(frames, features, locale) → dict`:
median metrics, stability per metric, readings with `support`,
element consensus, coverage map, skipped reasons (added by the MCP
tool), disclaimer, provenance.

MCP: `analyze_face_archive(photo_paths?, metrics_list?, features?,
locale)` — the archive twin of `analyze_face`.
