"""Transit calculations built on aspect detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from ..policies import orbs
from .aspects import ASPECT_ANGLES, _delta_angle


@dataclass
class Transit:
    transiting: str
    natal: str
    aspect: str
    orb: float
    applying: bool
    exact_datetime: datetime


def detect_transits(transiting_states: Iterable[dict], natal_states: Iterable[dict]) -> List[Transit]:
    results: List[Transit] = []
    for transit in transiting_states:
        for natal in natal_states:
            angle = abs(_delta_angle(transit["longitude"], natal["longitude"]))
            for aspect_name, target in ASPECT_ANGLES.items():
                orb_limit = orbs.transit_orb_for(transit["name"])
                delta = abs(angle - target)
                if delta <= orb_limit:
                    applying = _is_applying(transit, natal, target)
                    results.append(
                        Transit(
                            transiting=transit["name"],
                            natal=natal["name"],
                            aspect=aspect_name,
                            orb=delta,
                            applying=applying,
                            exact_datetime=transit.get("datetime") or datetime.utcnow(),
                        )
                    )
    return results


def _is_applying(transit: dict, natal: dict, target_angle: float) -> bool:
    delta_now = _delta_angle(transit["longitude"] - target_angle, natal["longitude"])
    dt = 0.1
    future_transit = transit["longitude"] + transit["speed"] * dt
    future_delta = _delta_angle(future_transit - target_angle, natal["longitude"])
    return abs(future_delta) < abs(delta_now)
