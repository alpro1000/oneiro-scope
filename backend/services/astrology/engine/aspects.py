"""Aspect detection with applying/separating classification."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List

from ..policies import orbs

ASPECT_ANGLES = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}


@dataclass
class BodyState:
    name: str
    longitude: float
    speed: float


@dataclass
class AspectResult:
    planet1: str
    planet2: str
    aspect: str
    orb: float
    applying: bool


def _normalize_angle(angle: float) -> float:
    return angle % 360


def _delta_angle(angle_a: float, angle_b: float) -> float:
    diff = _normalize_angle(angle_a - angle_b)
    return diff if diff <= 180 else diff - 360


def detect_aspects(bodies: Iterable[BodyState]) -> List[AspectResult]:
    body_list = list(bodies)
    results: List[AspectResult] = []
    for i, first in enumerate(body_list):
        for second in body_list[i + 1 :]:
            angle = abs(_delta_angle(second.longitude, first.longitude))
            for aspect_name, target in ASPECT_ANGLES.items():
                orb_limit = orbs.natal_orb_for(first.name)
                delta = abs(angle - target)
                if delta <= orb_limit:
                    applying = _is_applying(first, second, target)
                    results.append(
                        AspectResult(
                            planet1=first.name,
                            planet2=second.name,
                            aspect=aspect_name,
                            orb=delta,
                            applying=applying,
                        )
                    )
    return results


def _is_applying(first: BodyState, second: BodyState, target_angle: float) -> bool:
    delta_now = _delta_angle(second.longitude - target_angle, first.longitude)
    dt = 0.1  # days
    lon_first_future = first.longitude + first.speed * dt
    lon_second_future = second.longitude + second.speed * dt
    delta_future = _delta_angle(lon_second_future - target_angle, lon_first_future)
    return abs(delta_future) < abs(delta_now)
