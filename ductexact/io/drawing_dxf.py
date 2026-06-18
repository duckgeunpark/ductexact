"""완성도(AssemblyDrawing) -> DXF. 정투상 뷰 + 실제 선형 치수(ezdxf)."""
from __future__ import annotations

import ezdxf

from ..core.drawing import AssemblyDrawing
from ..core.units import from_mm

_INSUNITS = {"mm": 4, "cm": 5, "m": 6, "in": 1, "ft": 2}


def export_drawing(drawing: AssemblyDrawing, path: str, out_unit: str = "mm",
                   gap: float = 120.0) -> str:
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = _INSUNITS.get(out_unit, 4)
    msp = doc.modelspace()
    for name, color in (("OUTLINE", 7), ("FOLD", 3), ("DIM", 1), ("TEXT", 2)):
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    doc.layers.get("FOLD").dxf.linetype = "DASHED"

    def cv(v):
        return from_mm(v, out_unit)

    cursor = 0.0
    gap_u = cv(gap)
    for view in drawing.views:
        x0, y0, x1, y1 = view.bbox()
        off_x = cursor - cv(x0)
        off_y = -cv(y0)

        def P(pt):
            return (cv(pt[0]) + off_x, cv(pt[1]) + off_y)

        for pl in view.polylines:
            msp.add_lwpolyline([P(pt) for pt in pl], dxfattribs={"layer": "OUTLINE"})
        for cx, cy, r in view.circles:
            msp.add_circle(P((cx, cy)), cv(r), dxfattribs={"layer": "OUTLINE"})
        for a, b in view.fold_lines:
            msp.add_line(P(a), P(b), dxfattribs={"layer": "FOLD"})
        for d in view.dims:
            try:
                dim = msp.add_linear_dim(
                    base=P(d.base), p1=P(d.p1), p2=P(d.p2),
                    angle=d.angle, text=(d.text or "<>"),
                    dxfattribs={"layer": "DIM"})
                dim.render()
            except Exception:  # noqa: BLE001 - 치수 실패해도 도면은 출력
                pass
        # 뷰 제목
        msp.add_text(view.name, height=cv(16),
                     dxfattribs={"layer": "TEXT"}).set_placement(
            (cursor, off_y + cv(y1 - y0) + cv(20)))
        for lb in view.labels:
            msp.add_text(lb.text, height=cv(12),
                         dxfattribs={"layer": "TEXT"}).set_placement(P(lb.pos))
        cursor += cv(x1 - x0) + gap_u

    doc.saveas(path)
    return path
