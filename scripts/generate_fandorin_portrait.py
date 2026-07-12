#!/usr/bin/env python3
"""Generate the 50-year-old Erast Fandorin portrait via OpenAI gpt-image-1.

Prompt is reverse-engineered from Fandorin's book canon through the
OneiroScope physiognomy KB (mianxiang Metal/Wood + Corman/Kretschmer).
See docs/specs/fandorin-portrait/portrait-reverse-prompt.md.

Two modes:
  generate  — make a portrait from scratch using the canon prompt.
  edit      — rework an existing portrait (e.g. Akunin's variant),
              applying only the 4 canon fixes: grey temples, younger look,
              cooler gaze, thinner mustache.

Usage:
  export OPENAI_API_KEY=sk-...
  python scripts/generate_fandorin_portrait.py
  python scripts/generate_fandorin_portrait.py --n 4 --size 1024x1536
  python scripts/generate_fandorin_portrait.py --mode edit --reference akunin.png

Needs `openai` (in backend/requirements.txt). If the pinned version rejects
the model/size, run `pip install -U openai`.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from datetime import datetime
from pathlib import Path

# --- Canon prompt (reverse-mapped from character traits to facial features) ---

PROMPT = (
    "Portrait of a Russian aristocrat-detective, age 50 but looking about "
    "38-40, exceptionally youthful and athletic, disciplined upright bearing. "
    "Narrow, vertically elongated face with fine aristocratic 'minted' "
    "features, straight nose, high but NOT hollow cheekbones, fair clear skin. "
    "Jet-black thick neatly groomed hair; temples distinctly silver-grey — a "
    "sharp contrast against the black (this is the key signature, it must be "
    "clearly visible). Small neat dark mustache. Cool, calm, pale-blue eyes "
    "with an intelligent, slightly ironic, self-possessed gaze — not sad, not "
    "soft. Unsmiling but serene mouth. Belle Epoque dandy: black frock coat, "
    "high white wing collar. Late imperial Russia, circa 1906. Realistic "
    "oil-portrait style, restrained, dignified. "
    "Avoid: gaunt or hollow face, tired or sad eyes, looking older than 45, "
    "grey stubble or beard, heavy jaw, wide face, romantic melancholy, dark "
    "(non-grey) temples, warm or soft gaze."
)

# For edit mode: keep the good base, change only what reads wrong vs canon.
EDIT_PROMPT = (
    "Keep this man's face, pose, clothing (black coat, high white wing collar) "
    "and overall composition. Apply only these corrections so he matches the "
    "canonical Erast Fandorin at 50: "
    "(1) make the temples distinctly silver-grey with a sharp contrast against "
    "the black hair — this is his signature; "
    "(2) make him look 7-10 years younger — fill the hollow cheeks slightly, "
    "fresher and firmer skin, athletic not tired; "
    "(3) cool the gaze — calm, composed, slightly ironic pale-blue eyes, "
    "remove the sad/soft expression; "
    "(4) make the mustache thinner and neater. "
    "Realistic oil-portrait style, restrained, dignified."
)


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("openai package not installed. Run: pip install -U openai")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY is not set. Export it and retry.")
    return OpenAI(api_key=key)


def _save(b64_list, out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    paths = []
    for i, b64 in enumerate(b64_list):
        suffix = f"-{i + 1}" if len(b64_list) > 1 else ""
        path = out_dir / f"{stem}-{stamp}{suffix}.png"
        path.write_bytes(base64.b64decode(b64))
        paths.append(path)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the Fandorin portrait.")
    ap.add_argument("--mode", choices=["generate", "edit"], default="generate")
    ap.add_argument("--reference", help="reference PNG/JPG for edit mode")
    ap.add_argument("--prompt", help="override the built-in prompt")
    ap.add_argument("--size", default="1024x1536",
                    help="1024x1536 (portrait), 1024x1024, 1536x1024, auto")
    ap.add_argument("--n", type=int, default=1, help="number of images")
    ap.add_argument("--out", default="docs/specs/fandorin-portrait/output",
                    help="output directory")
    args = ap.parse_args()

    client = _client()
    out_dir = Path(args.out)

    if args.mode == "edit":
        if not args.reference:
            sys.exit("edit mode needs --reference <image path>")
        ref = Path(args.reference)
        if not ref.exists():
            sys.exit(f"reference not found: {ref}")
        prompt = args.prompt or EDIT_PROMPT
        print(f"Editing {ref} with gpt-image-1 (n={args.n}, size={args.size})…")
        with ref.open("rb") as fh:
            resp = client.images.edit(
                model="gpt-image-1", image=fh, prompt=prompt,
                size=args.size, n=args.n,
            )
        stem = "fandorin-edit"
    else:
        prompt = args.prompt or PROMPT
        print(f"Generating with gpt-image-1 (n={args.n}, size={args.size})…")
        resp = client.images.generate(
            model="gpt-image-1", prompt=prompt, size=args.size, n=args.n,
        )
        stem = "fandorin"

    b64_list = [d.b64_json for d in resp.data if d.b64_json]
    if not b64_list:
        sys.exit("API returned no image data.")
    paths = _save(b64_list, out_dir, stem)
    print("Saved:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
