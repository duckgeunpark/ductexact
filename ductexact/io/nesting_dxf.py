"""네스팅 결과 -> DXF. 시트마다 경계 + 배치된 패널(외형/접기선)."""
from __future__ import annotations

import ezdxf

from ..core.nesting import NestResult
from ..core.units import from_mm

_INSUNITS = {"mm": 4, "cm": 5, "m": 6, "in": 1, "ft": 2}


def export_nesting(result: NestResult, path: str, out_unit: str = "mm",
                   sheet_gap: float = 200.0) -> str:
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = _INSUNITS.get(out_unit, 4)
    msp = doc.modelspace()
    for name, color in (("SHEET", 5), ("OUTLINE", 7), ("FOLD", 3),
                        ("MARK", 30), ("TEXT", 2)):
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    doc.layers.get("FOLD").dxf.linetype = "DASHED"
    doc.layers.get("MARK").dxf.linetype = "DASHDOT"

    def cv(v):
        return from_mm(v, out_unit)

    ox = 0.0
    for i, sheet in enumerate(result.sheets):
        sw, sh = cv(sheet.width), cv(sheet.height)
        # 시트 경계
        msp.add_lwpolyline(
            [(ox, 0), (ox + sw, 0), (ox + sw, sh), (ox, sh)],
            close=True, dxfattribs={"layer": "SHEET"})
        msp.add_text(f"Sheet {i+1}  ({sheet.utilization()*100:.0f}%)",
                     height=cv(20),
                     dxfattribs={"layer": "TEXT"}).set_placement((ox, -cv(30)))
        for pl in sheet.placements:
            pts = [(cv(x) + ox, cv(y)) for x, y in pl.outline]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "OUTLINE"})
            for a, b in pl.fold_lines:
                msp.add_line((cv(a[0]) + ox, cv(a[1])),
                             (cv(b[0]) + ox, cv(b[1])),
                             dxfattribs={"layer": "FOLD"})
            for a, b in pl.mark_lines:
                msp.add_line((cv(a[0]) + ox, cv(a[1])),
                             (cv(b[0]) + ox, cv(b[1])),
                             dxfattribs={"layer": "MARK"})
        ox += sw + cv(sheet_gap)

    doc.saveas(path)
    return path
