from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Tuple

__all__ = ["set_ephe_path", "julday", "lun_phase"]


_ephe_path: Path | None = None


def set_ephe_path(path: str | Path) -> None:
    global _ephe_path
    _ephe_path = Path(path)


def julday(year: int, month: int, day: int) -> float:
    """Simplified Julian day computation.

    This is not astronomically precise but provides a deterministic input for
    the lunar phase helper without heavy native dependencies.
    """

    # date.toordinal is close enough for our pseudo calculations
    return float(date(year, month, day).toordinal())


def lun_phase(julian_day: float) -> float:
    """Return a pseudo lunar phase in the range [0, 1].

    Uses a sine wave over the Julian day to emulate waxing/waning cycles.
    """

    cycle = 29.53058867  # average synodic month length
    phase = (julian_day % cycle) / cycle
    # normalize using sine to keep values between 0 and 1 and smooth transitions
    return (math.sin(phase * 2 * math.pi) + 1) / 2
