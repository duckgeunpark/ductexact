"""Pattern -> DXF. 레이어 분리(OUTLINE/FOLD/DIM/TEXT), 패널 자동 나열."""
from __future__ import annotations

import ezdxf

from ..core.pattern import Pattern
from ..core.units import from_mm

# DXF $INSUNITS 코드
_INSUNITS = {"mm": 4, "cm": 5, "m": 6, "in": 1, "ft": 2}

_LAYERS = {
    "OUTLINE": 7,   # 흰/검 - 절단선
    "FOLD": 3,      # 초록 - 접기선(실제 절곡)
    "MARK": 30,     # 주황 - 여유 경계선(심·단부)
    "DIM": 1,       # 빨강 - 치수
    "TEXT": 2,      # 노랑 - 주석
}


def export_pattern(pattern: Pattern, path: str, out_unit: str = "mm",
                   gap: float = 50.0) -> str:
    """패턴을 DXF 파일로 저장. 좌표는 out_unit 으로 변환. 반환: 저장 경로."""
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = _INSUNITS.get(out_unit, 4)
    msp = doc.modelspace()

    for name, color in _LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    doc.layers.get("FOLD").dxf.linetype = "DASHED"
    doc.layers.get("MARK").dxf.linetype = "DASHDOT"

    def conv(pt):
        return (from_mm(pt[0], out_unit), from_mm(pt[1], out_unit))

    cursor_x = 0.0
    gap_u = from_mm(gap, out_unit)

    for panel in pattern.panels:
        w_mm, _ = panel.size()
        x0_mm, y0_mm, _, _ = panel.bbox()
        # 패널을 (cursor_x, 0) 으로 이동시키는 오프셋(out_unit)
        off_x = cursor_x - from_mm(x0_mm, out_unit)
        off_y = -from_mm(y0_mm, out_unit)

        def place(pt):
            x, y = conv(pt)
            return (x + off_x, y + off_y)

        # 외형
        pts = [place(p) for p in panel.outline]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "OUTLINE"})

        # 접기선
        for (a, b) in panel.fold_lines:
            msp.add_line(place(a), place(b), dxfattribs={"layer": "FOLD"})

        # 여유 경계선(심·단부)
        for (a, b) in panel.mark_lines:
            msp.add_line(place(a), place(b), dxfattribs={"layer": "MARK"})

        # 패널 라벨
        label = f"{panel.name}  x{panel.qty}"
        msp.add_text(label, height=from_mm(8, out_unit),
                     dxfattribs={"layer": "TEXT"}).set_placement(
            (cursor_x, -from_mm(15, out_unit)))

        # 내부 주석
        for (tx, ty, txt) in panel.texts:
            msp.add_text(txt, height=from_mm(6, out_unit),
                         dxfattribs={"layer": "TEXT"}).set_placement(place((tx, ty)))

        cursor_x += from_mm(w_mm, out_unit) + gap_u

    doc.saveas(path)
    return path
