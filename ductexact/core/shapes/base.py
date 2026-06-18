"""형상 추상 클래스 + 파라미터 명세 + 공통 설정."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..pattern import Pattern
from ..units import to_mm, DEFAULT_LENGTH_UNIT
from .. import allowances as al


@dataclass
class ParamSpec:
    """입력칸 한 개의 명세. GUI 가 이걸로 폼을 자동 생성한다."""

    key: str                 # 내부 키
    label: str               # 화면 표시명(한글)
    kind: str = "length"     # "length" | "angle" | "int" | "choice"
    default: float = 0.0
    default_unit: str = DEFAULT_LENGTH_UNIT
    minimum: float = 0.0
    maximum: float = 1e9
    choices: list[str] = field(default_factory=list)   # kind=="choice"
    help: str = ""


@dataclass
class CommonSettings:
    """모든 형상 공통 제작 설정 (mm 여유값은 테이블에서 조회)."""

    seam: str = "Pittsburgh"
    joint: str = "Angle Flange + Bolt"
    gauge: str = "18"
    output_unit: str = "mm"
    dim_basis: str = "ID"          # ID(내경) / OD(외경)
    use_bend_allowance: bool = False
    k_factor: float = 0.5          # 중립선 위치 (0=내면, 0.5=중앙)
    # 여유값 테이블 (defaults.json 에서 주입; None 이면 allowances 모듈 기본값)
    seam_table: dict | None = None
    end_table: dict | None = None
    gauge_table: dict | None = None

    def thickness(self) -> float:
        """선택 게이지의 판 두께(mm)."""
        return al.gauge_thickness(self.gauge, self.gauge_table)

    def to_neutral(self, value: float) -> float:
        """입력 단면치수를 전개 기준인 중립선 치수(mm)로 보정.

        ID(내경) 입력  -> 중립선 = ID + 2·k·t
        OD(외경) 입력  -> 중립선 = OD - 2·(1-k)·t
        굽힘여유 미사용 시 k=0 (내경=그대로, 외경=내경으로).
        """
        t = self.thickness()
        k = self.k_factor if self.use_bend_allowance else 0.0
        if self.dim_basis == "OD":
            return value - 2.0 * (1.0 - k) * t
        return value + 2.0 * k * t


class Shape:
    """형상 베이스. 하위 클래스는 key/name/params/develop 만 채우면 된다."""

    key: str = "base"
    name: str = "Base"
    description: str = ""

    #: list[ParamSpec]
    params: list[ParamSpec] = []

    @classmethod
    def param_values_to_mm(cls, raw: dict[str, tuple[float, str]]) -> dict[str, float]:
        """raw[key]=(value, unit) -> {key: mm 또는 원시값(int/angle)}."""
        out: dict[str, float] = {}
        spec_by_key = {p.key: p for p in cls.params}
        for k, (val, unit) in raw.items():
            spec = spec_by_key.get(k)
            if spec is None:
                continue
            if spec.kind == "length":
                out[k] = to_mm(val, unit)
            else:  # angle / int / choice 는 그대로
                out[k] = val
        return out

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        """p: mm 정규화된 파라미터. -> Pattern. 하위 클래스 구현."""
        raise NotImplementedError
