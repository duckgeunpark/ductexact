"""단위 처리: 내부 기준은 mm. 입력칸마다 단위를 개별 선택할 수 있다."""
from __future__ import annotations

from dataclasses import dataclass

# 길이 단위 -> mm 변환 계수
LENGTH_UNITS: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "ft": 304.8,
}

# 각도 단위 (변환 없이 deg 사용, 확장 여지용)
ANGLE_UNITS: dict[str, float] = {
    "deg": 1.0,
}

DEFAULT_LENGTH_UNIT = "mm"


def to_mm(value: float, unit: str) -> float:
    """주어진 길이 값을 mm 로 변환."""
    try:
        return float(value) * LENGTH_UNITS[unit]
    except KeyError as exc:  # pragma: no cover - 방어적
        raise ValueError(f"알 수 없는 길이 단위: {unit!r}") from exc


def from_mm(value_mm: float, unit: str) -> float:
    """mm 값을 지정 단위로 변환."""
    try:
        return float(value_mm) / LENGTH_UNITS[unit]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"알 수 없는 길이 단위: {unit!r}") from exc


@dataclass(frozen=True)
class UnitValue:
    """값 + 단위 묶음. GUI 입력칸 하나에 대응."""

    value: float
    unit: str = DEFAULT_LENGTH_UNIT

    def to_mm(self) -> float:
        return to_mm(self.value, self.unit)

    @classmethod
    def from_mm(cls, value_mm: float, unit: str = DEFAULT_LENGTH_UNIT) -> "UnitValue":
        return cls(from_mm(value_mm, unit), unit)

    def __str__(self) -> str:
        return f"{self.value:g} {self.unit}"
