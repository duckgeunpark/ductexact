"""완성도(정투상 조립도) 자료구조 + 치수선 미리보기 전개.

좌표 단위 mm. 각 형상이 동일한 AssemblyDrawing 을 반환 -> 미리보기/DXF 공용.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Point = tuple[float, float]


@dataclass
class LinearDim:
    """선형 치수. angle=0 수평(가로거리), 90 수직(세로거리)."""

    p1: Point
    p2: Point
    base: Point                  # 치수선이 놓이는 위치(한 점)
    angle: float = 0.0
    text: str | None = None      # None 이면 거리 자동


@dataclass
class Label:
    pos: Point
    text: str


@dataclass
class View:
    name: str
    polylines: list[list[Point]] = field(default_factory=list)
    circles: list[tuple[float, float, float]] = field(default_factory=list)  # cx,cy,r
    fold_lines: list[tuple[Point, Point]] = field(default_factory=list)  # 접기/절곡선(점선)
    dims: list[LinearDim] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)

    def bbox(self) -> tuple[float, float, float, float]:
        xs: list[float] = []
        ys: list[float] = []
        for pl in self.polylines:
            for x, y in pl:
                xs.append(x); ys.append(y)
        for cx, cy, r in self.circles:
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
        for a, b in self.fold_lines:
            xs += [a[0], b[0]]; ys += [a[1], b[1]]
        for d in self.dims:
            for p in (d.p1, d.p2, d.base):
                xs.append(p[0]); ys.append(p[1])
        if not xs:
            return 0, 0, 0, 0
        return min(xs), min(ys), max(xs), max(ys)


@dataclass
class AssemblyDrawing:
    shape_name: str
    views: list[View] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ---------- 미리보기용 치수선 전개 ----------
def dim_geometry(d: LinearDim, arrow: float = 12.0, ext: float = 4.0):
    """치수선을 (선분리스트, (텍스트위치, 텍스트, 각도)) 로 전개 (미리보기용)."""
    p1, p2, base = d.p1, d.p2, d.base
    segs: list[tuple[Point, Point]] = []
    if d.angle == 0:  # 수평: y=base[1] 에 치수선, x 거리 측정
        ly = base[1]
        x1, x2 = p1[0], p2[0]
        segs.append(((x1, p1[1]), (x1, ly + math.copysign(ext, ly - p1[1]) if ly != p1[1] else ly)))
        segs.append(((x2, p2[1]), (x2, ly + math.copysign(ext, ly - p2[1]) if ly != p2[1] else ly)))
        segs.append(((x1, ly), (x2, ly)))
        for xa in (x1, x2):
            sgn = 1 if xa == min(x1, x2) else -1
            segs.append(((xa, ly), (xa + sgn * arrow, ly + arrow * 0.35)))
            segs.append(((xa, ly), (xa + sgn * arrow, ly - arrow * 0.35)))
        val = d.text if d.text is not None else f"{abs(x2 - x1):.0f}"
        return segs, ((min(x1, x2) + max(x1, x2)) / 2, ly), val, 0
    else:  # 수직
        lx = base[0]
        y1, y2 = p1[1], p2[1]
        segs.append(((p1[0], y1), (lx + math.copysign(ext, lx - p1[0]) if lx != p1[0] else lx, y1)))
        segs.append(((p2[0], y2), (lx + math.copysign(ext, lx - p2[0]) if lx != p2[0] else lx, y2)))
        segs.append(((lx, y1), (lx, y2)))
        for ya in (y1, y2):
            sgn = 1 if ya == min(y1, y2) else -1
            segs.append(((lx, ya), (lx + arrow * 0.35, ya + sgn * arrow)))
            segs.append(((lx, ya), (lx - arrow * 0.35, ya + sgn * arrow)))
        val = d.text if d.text is not None else f"{abs(y2 - y1):.0f}"
        return segs, (lx, (min(y1, y2) + max(y1, y2)) / 2), val, 90
