"""형상 레지스트리."""
from __future__ import annotations

from .base import Shape, ParamSpec, CommonSettings
from .rect_straight import RectStraight
from .round_straight import RoundStraight
from .rect_elbow import RectElbow
from .round_elbow import RoundElbow
from .reducer import Reducer
from .tee import RoundTee, RectTee

# GUI 좌측 목록 순서
SHAPES: list[type[Shape]] = [
    RectStraight,
    RoundStraight,
    RectElbow,
    RoundElbow,
    Reducer,
    RoundTee,
    RectTee,
]

SHAPES_BY_KEY = {s.key: s for s in SHAPES}

__all__ = [
    "Shape", "ParamSpec", "CommonSettings",
    "RectStraight", "RoundStraight", "RectElbow", "RoundElbow", "Reducer",
    "RoundTee", "RectTee",
    "SHAPES", "SHAPES_BY_KEY",
]
