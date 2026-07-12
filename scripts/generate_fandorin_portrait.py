#!/usr/bin/env python3
"""Generate the 50-year-old Erast Fandorin portrait (OpenAI or Google Gemini).

Prompt is reverse-engineered from Fandorin's book canon through the
OneiroScope physiognomy KB (mianxiang Metal/Wood + Corman/Kretschmer).
See docs/specs/fandorin-portrait/portrait-reverse-prompt.md.

Providers (--provider):
  openai  — gpt-image-1              (needs OPENAI_API_KEY, `openai`)
  gemini  — gemini-2.5-flash-image  (needs GEMINI_API_KEY, `google-genai`)

Modes (--mode):
  generate  — make a portrait from scratch using the canon prompt.
  edit      — rework an existing portrait (e.g. Akunin's variant), applying
              only the 4 canon fixes: grey temples, younger, cooler gaze,
              thinner mustache. Both providers support edit via a reference.

Usage:
  export OPENAI_API_KEY=sk-...   # or: export GEMINI_API_KEY=...
  python scripts/generate_fandorin_portrait.py
  python scripts/generate_fandorin_portrait.py --provider gemini --n 4
  python scripts/generate_fandorin_portrait.py --mode edit --reference akunin.png
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

# Map --size to an aspect hint for Gemini (which takes orientation, not pixels).
_ASPECT = {"1024x1536": "3:4 (vertical portrait)", "1536x1024": "4:3",
           "1024x1024": "1:1 (square)"}


def _mime(path: Path) -> str:
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
        path.suffix.lower().lstrip("."), "image/png")


# --- OpenAI (gpt-image-1) ---------------------------------------------------

def run_openai(mode, prompt, size, n, reference) -> list[bytes]:
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("openai not installed. Run: pip install -U openai")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY is not set. Export it and retry.")
    client = OpenAI(api_key=key)

    if mode == "edit":
        with reference.open("rb") as fh:
            resp = client.images.edit(model="gpt-image-1", image=fh,
                                      prompt=prompt, size=size, n=n)
    else:
        resp = client.images.generate(model="gpt-image-1", prompt=prompt,
                                       size=size, n=n)
    return [base64.b64decode(d.b64_json) for d in resp.data if d.b64_json]


# --- Google Gemini (gemini-2.5-flash-image, aka Nano Banana) ----------------

def run_gemini(mode, prompt, size, n, reference) -> list[bytes]:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("google-genai not installed. Run: pip install google-genai")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set. Export it and retry.")
    client = genai.Client(api_key=key)
    model = "gemini-2.5-flash-image"

    if mode == "edit":
        contents = [prompt, types.Part.from_bytes(
            data=reference.read_bytes(), mime_type=_mime(reference))]
    else:
        contents = [f"{prompt} Orientation: {_ASPECT.get(size, '3:4')}."]

    # generate_content returns one image per call; loop for n.
    images: list[bytes] = []
    for _ in range(n):
        resp = client.models.generate_content(model=model, contents=contents)
        for part in resp.candidates[0].content.parts:
            data = getattr(getattr(part, "inline_data", None), "data", None)
            if data:
                images.append(data)
    return images


PROVIDERS = {"openai": run_openai, "gemini": run_gemini}


def _save(images: list[bytes], out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    paths = []
    for i, data in enumerate(images):
        suffix = f"-{i + 1}" if len(images) > 1 else ""
        path = out_dir / f"{stem}-{stamp}{suffix}.png"
        path.write_bytes(data)
        paths.append(path)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the Fandorin portrait.")
    ap.add_argument("--provider", choices=list(PROVIDERS), default="openai")
    ap.add_argument("--mode", choices=["generate", "edit"], default="generate")
    ap.add_argument("--reference", help="reference PNG/JPG for edit mode")
    ap.add_argument("--prompt", help="override the built-in prompt")
    ap.add_argument("--size", default="1024x1536",
                    help="openai: 1024x1536|1024x1024|1536x1024|auto; "
                         "gemini: used only as an aspect hint")
    ap.add_argument("--n", type=int, default=1, help="number of images")
    ap.add_argument("--out", default="docs/specs/fandorin-portrait/output",
                    help="output directory")
    args = ap.parse_args()

    reference = None
    if args.mode == "edit":
        if not args.reference:
            sys.exit("edit mode needs --reference <image path>")
        reference = Path(args.reference)
        if not reference.exists():
            sys.exit(f"reference not found: {reference}")
        prompt = args.prompt or EDIT_PROMPT
        stem = "fandorin-edit"
    else:
        prompt = args.prompt or PROMPT
        stem = "fandorin"

    print(f"{args.provider} · {args.mode} · n={args.n} · size={args.size} …")
    images = PROVIDERS[args.provider](args.mode, prompt, args.size, args.n,
                                      reference)
    if not images:
        sys.exit("Provider returned no image data.")
    print("Saved:")
    for p in _save(images, Path(args.out), stem):
        print(f"  {p}")


if __name__ == "__main__":
    main()
