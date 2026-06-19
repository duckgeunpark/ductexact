"""전개 결과 표준 자료구조. 모든 형상이 동일한 Pattern 을 반환한다.

좌표 단위는 항상 mm (내부 표준).  DXF/표/미리보기가 이 구조를 공용으로 사용.
"""
from __future__ import annotations

from dataclasses import dataclass, field

Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass
class Panel:
    """절단할 판재 한 장의 전개 형상."""

    name: str
    outline: list[Point]                       # 닫힌 외형(절단선) 폴리라인
    qty: int = 1                               # 동일 패널 매수
    fold_lines: list[Segment] = field(default_factory=list)   # 접기선(실제 절곡)
    mark_lines: list[Segment] = field(default_factory=list)   # 여유 경계선(심·단부)
    curves: list[dict] = field(default_factory=list)          # 도해표용 곡선 정의(원호/공식)
    texts: list[tuple[float, float, str]] = field(default_factory=list)  # 주석

    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        return min(xs), min(ys), max(xs), max(ys)

    def size(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.bbox()
        return x1 - x0, y1 - y0


@dataclass
class Pattern:
    """한 형상의 전체 전개 결과."""

    shape_name: str
    panels: list[Panel] = field(default_factory=list)
    table: list[dict] = field(default_factory=list)   # 치수표 행들
    notes: list[str] = field(default_factory=list)

    def add_panel(self, panel: Panel) -> None:
        self.panels.append(panel)

    def add_row(self, **row) -> None:
        self.table.append(row)
