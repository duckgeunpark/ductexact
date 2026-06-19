"""판재 네스팅: 패널 bbox 기준 셸프 패킹(FFD). 단위 mm.

bbox 기반 직사각형 배치로 단순·견고함을 우선한다(불규칙 윤곽 맞물림은 후속).
회전(90°) 옵션 지원.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .pattern import Pattern, Panel, Point


@dataclass
class Placement:
    name: str
    outline: list[Point]               # 시트 좌표로 배치된 외형
    fold_lines: list = field(default_factory=list)
    mark_lines: list = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    rotated: bool = False


@dataclass
class Sheet:
    width: float
    height: float
    placements: list[Placement] = field(default_factory=list)

    def used_area(self) -> float:
        from . import geometry as g
        return sum(g.polygon_area(p.outline) for p in self.placements)

    def utilization(self) -> float:
        if self.width * self.height == 0:
            return 0.0
        return self.used_area() / (self.width * self.height)


@dataclass
class NestResult:
    sheets: list[Sheet]
    unplaced: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        total = sum(s.width * s.height for s in self.sheets)
        used = sum(s.used_area() for s in self.sheets)
        return {
            "sheets": len(self.sheets),
            "utilization": (used / total) if total else 0.0,
            "unplaced": len(self.unplaced),
        }


def _normalize(pts: list[Point]) -> tuple[list[Point], float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ox, oy = min(xs), min(ys)
    norm = [(x - ox, y - oy) for x, y in pts]
    w = max(xs) - ox
    h = max(ys) - oy
    return norm, w, h


def _rot90(pts: list[Point]) -> list[Point]:
    """원점 기준 +90° 회전 후 양수 영역으로."""
    r = [(-y, x) for x, y in pts]
    n, _, _ = _normalize(r)
    return n


def _seg_offset(segs, ox, oy):
    return [((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy)) for a, b in segs]


@dataclass
class _Item:
    name: str
    outline: list[Point]
    folds: list
    marks: list
    w: float
    h: float


def _expand(patterns: list[Pattern], gap: float) -> list[_Item]:
    items: list[_Item] = []
    for pat in patterns:
        for panel in pat.panels:
            norm, w, h = _normalize(panel.outline)
            # fold/mark 도 같은 원점으로
            xs = [p[0] for p in panel.outline]
            ys = [p[1] for p in panel.outline]
            ox, oy = min(xs), min(ys)
            folds = _seg_offset(panel.fold_lines, -ox, -oy)
            marks = _seg_offset(panel.mark_lines, -ox, -oy)
            for _ in range(max(panel.qty, 1)):
                items.append(_Item(panel.name, norm, folds, marks, w, h))
    return items


def nest(patterns: list[Pattern], sheet_w: float, sheet_h: float,
         gap: float = 10.0, allow_rotate: bool = True) -> NestResult:
    """패턴들의 모든 패널(매수 포함)을 시트에 셸프 패킹."""
    items = _expand(patterns, gap)
    # 큰 것부터 (높이 내림차순)
    items.sort(key=lambda it: max(it.w, it.h), reverse=True)

    sheets: list[Sheet] = []
    unplaced: list[str] = []

    def fits(w, h):
        return w <= sheet_w + 1e-6 and h <= sheet_h + 1e-6

    # 각 시트의 셸프: (y_base, shelf_h, cursor_x)
    shelves_per_sheet: list[list[list[float]]] = []

    def place_on_sheet(si, it) -> bool:
        sheet = sheets[si]
        shelves = shelves_per_sheet[si]
        for orient in _orientations(it, allow_rotate, sheet_w, sheet_h):
            w, h, outline, folds, marks, rotated = orient
            # 기존 셸프 first-fit
            for sh in shelves:
                y_base, shelf_h, cursor_x = sh
                if h <= shelf_h + 1e-6 and cursor_x + w <= sheet_w + 1e-6:
                    _commit(sheet, it, outline, folds, marks, cursor_x, y_base, rotated)
                    sh[2] = cursor_x + w + gap
                    return True
            # 새 셸프
            top = (shelves[-1][0] + shelves[-1][1] + gap) if shelves else 0.0
            if top + h <= sheet_h + 1e-6 and w <= sheet_w + 1e-6:
                shelves.append([top, h, w + gap])
                _commit(sheet, it, outline, folds, marks, 0.0, top, rotated)
                return True
        return False

    for it in items:
        if not fits(it.w, it.h) and not (allow_rotate and fits(it.h, it.w)):
            unplaced.append(it.name)
            continue
        placed = False
        for si in range(len(sheets)):
            if place_on_sheet(si, it):
                placed = True
                break
        if not placed:
            sheets.append(Sheet(sheet_w, sheet_h))
            shelves_per_sheet.append([])
            if not place_on_sheet(len(sheets) - 1, it):
                unplaced.append(it.name)

    return NestResult(sheets, unplaced)


def _orientations(it: _Item, allow_rotate: bool, sw: float, sh: float):
    """배치 후보(높이 작은 순). (w,h,outline,folds,marks,rotated)."""
    cands = [(it.w, it.h, it.outline, it.folds, it.marks, False)]
    if allow_rotate:
        rout = _rot90(it.outline)
        rfold = [((-a[1], a[0]), (-b[1], b[0])) for a, b in it.folds]
        rmark = [((-a[1], a[0]), (-b[1], b[0])) for a, b in it.marks]
        # rot fold/mark 정규화 위해 outline 기준 동일 오프셋 적용
        rfold = _renorm_folds(it.outline, rfold)
        rmark = _renorm_folds(it.outline, rmark)
        cands.append((it.h, it.w, rout, rfold, rmark, True))
    cands = [c for c in cands if c[0] <= sw + 1e-6 and c[1] <= sh + 1e-6]
    cands.sort(key=lambda c: c[1])
    return cands


def _renorm_folds(orig_outline, rotated_folds):
    # 회전된 외형의 최소점만큼 fold 이동
    r = [(-y, x) for x, y in orig_outline]
    xs = [p[0] for p in r]
    ys = [p[1] for p in r]
    ox, oy = min(xs), min(ys)
    return [((a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy)) for a, b in rotated_folds]


def _commit(sheet, it, outline, folds, marks, x, y, rotated):
    out = [(px + x, py + y) for px, py in outline]
    fl = [((a[0] + x, a[1] + y), (b[0] + x, b[1] + y)) for a, b in folds]
    mk = [((a[0] + x, a[1] + y), (b[0] + x, b[1] + y)) for a, b in marks]
    sheet.placements.append(Placement(it.name, out, fl, mk, x, y, rotated))
