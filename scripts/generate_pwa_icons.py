#!/usr/bin/env python3
"""Generate the PWA icons declared in `frontend/public/manifest.json`.

Committed as a generator rather than as three opaque PNGs: an icon is
a design decision, and a decision that exists only as pixels cannot be
reviewed, re-rendered at a new size, or corrected without redrawing it
by hand. Run it and the files below are reproduced byte for byte.

    python3 scripts/generate_pwa_icons.py

No Pillow, no fonts, no network — the PNG encoder is thirty lines of
zlib and struct, so this keeps working on any machine that can run the
backend at all. The mark is a crescent over a horizon line: the moon for
the lunar calendar and dreams, the horizon for the Ascendant, which is
what the whole chart hangs on.

`purpose: "maskable"` is a separate file for a real reason: Android
crops icons to a platform-chosen shape, and anything outside the central
80% circle can be cut. The maskable variant therefore draws the same
mark at 62% scale, so no shape crops into it.
"""

from __future__ import annotations

import math
import pathlib
import struct
import zlib

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "frontend/public/icons"

# Matches manifest.json's background_color / theme_color so the splash
# screen and the icon do not visibly disagree at launch.
BG_TOP = (0x0B, 0x0D, 0x1A)
BG_BOTTOM = (0x1C, 0x18, 0x3A)
MOON = (0xF4, 0xEC, 0xD9)
HORIZON = (0x7C, 0x6C, 0xC4)
STAR = (0xCF, 0xC6, 0xF2)

SUPERSAMPLE = 3  # per axis; 9 samples per pixel is enough to hide the stairs


def _png(path: pathlib.Path, size: int, rows: list[list[tuple[int, int, int]]]) -> None:
    """Write an 8-bit RGB PNG. Filter type 0 on every row, deflate level 9."""
    raw = b"".join(
        b"\x00" + bytes(channel for px in row for channel in px) for row in rows
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _mix(under: tuple[float, float, float], over: tuple[int, int, int], alpha: float):
    return tuple(u + (o - u) * alpha for u, o in zip(under, over))


def _coverage(distance: float, radius: float, feather: float) -> float:
    """Soft edge: 1 well inside the shape, 0 well outside, ramped between."""
    return max(0.0, min(1.0, (radius - distance) / feather))


# Four sparkles, placed off the crescent's open side so they read as sky
# rather than as noise on the moon. (x, y, radius) in unit coordinates.
STARS = [(0.735, 0.255, 0.030), (0.815, 0.430, 0.018),
         (0.665, 0.150, 0.016), (0.255, 0.760, 0.020)]


def _sample(x: float, y: float, scale: float) -> tuple[float, float, float]:
    """Colour at unit coordinates (0..1), with the mark drawn at `scale`."""
    colour: tuple[float, float, float] = tuple(  # vertical gradient sky
        t + (b - t) * y for t, b in zip(BG_TOP, BG_BOTTOM)
    )

    # A faint glow behind the mark so the crescent has something to sit in.
    glow = math.hypot(x - 0.5, y - 0.46)
    colour = _mix(colour, (0x3A, 0x31, 0x6E), 0.30 * _coverage(glow, 0.42 * scale + 0.10, 0.55))

    def s(v: float) -> float:  # scale a length about the centre
        return v * scale

    feather = s(0.010) + 0.002

    for sx, sy, sr in STARS:
        px, py = 0.5 + (sx - 0.5) * scale, 0.5 + (sy - 0.5) * scale
        # Four-pointed sparkle: a superellipse-ish cross, not a dot.
        dx, dy = abs(x - px), abs(y - py)
        d = (dx ** 0.62 + dy ** 0.62) ** (1 / 0.62)
        colour = _mix(colour, STAR, 0.85 * _coverage(d, s(sr), feather))

    # Horizon — the Ascendant. Drawn before the moon so the moon sits on it.
    hy = 0.5 + (0.775 - 0.5) * scale
    span = _coverage(abs(x - 0.5), s(0.335), s(0.14))
    colour = _mix(colour, HORIZON, 0.9 * span * _coverage(abs(y - hy), s(0.019), feather))

    # Crescent: one disc minus another, offset up and to the right.
    moon = math.hypot(x - (0.5 - s(0.045)), y - (0.5 - s(0.075)))
    bite = math.hypot(x - (0.5 + s(0.105)), y - (0.5 - s(0.165)))
    lit = _coverage(moon, s(0.300), feather) * (1.0 - _coverage(bite, s(0.268), feather))
    return _mix(colour, MOON, lit)


def render(size: int, scale: float) -> list[list[tuple[int, int, int]]]:
    step = 1.0 / (size * SUPERSAMPLE)
    half = step / 2
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0.0, 0.0, 0.0]
            for sy in range(SUPERSAMPLE):
                y = (py * SUPERSAMPLE + sy) * step + half
                for sx in range(SUPERSAMPLE):
                    x = (px * SUPERSAMPLE + sx) * step + half
                    c = _sample(x, y, scale)
                    acc[0] += c[0]
                    acc[1] += c[1]
                    acc[2] += c[2]
            n = SUPERSAMPLE * SUPERSAMPLE
            row.append(tuple(max(0, min(255, round(v / n))) for v in acc))
        rows.append(row)
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # (filename, pixel size, mark scale). The maskable variant keeps the
    # mark inside the central 80% circle Android is allowed to crop to.
    for name, size, scale in (
        ("icon-192.png", 192, 1.0),
        ("icon-512.png", 512, 1.0),
        ("icon-maskable-512.png", 512, 0.62),
    ):
        path = OUT_DIR / name
        _png(path, size, render(size, scale))
        print(f"wrote {path.relative_to(OUT_DIR.parents[2])} ({path.stat().st_size} B)")


if __name__ == "__main__":
    main()
