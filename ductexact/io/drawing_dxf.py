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

    # 한글 문자가 ??로 깨지지 않도록 TrueType(맑은 고딕) 텍스트 스타일 정의.
    # (DXF 기본 스타일은 txt.shx — 한글 글리프가 없어 깨짐)
    KFONT = "HANGEUL"
    if KFONT not in doc.styles:
        doc.styles.add(KFONT, font="malgun.ttf")

    def cv(v):
        return from_mm(v, out_unit)

    # 치수/문자 크기를 도면 크기에 비례시켜 가독성 확보.
    # (ezdxf 기본 dimstyle 글자 높이는 0.25 수준이라 mm 도면에선 사실상 안 보임)
    char = 0.0
    for view in drawing.views:
        x0, y0, x1, y1 = view.bbox()
        char = max(char, cv(x1 - x0), cv(y1 - y0))
    if char <= 0:
        char = cv(100.0)
    txt_h = max(char * 0.03, cv(2.5))      # 치수/라벨 글자 높이
    dim_override = {
        "dimtxt": txt_h,                   # 치수 글자 높이
        "dimasz": txt_h * 0.9,             # 화살표 크기
        "dimexe": txt_h * 0.6,             # 치수 보조선 연장
        "dimexo": txt_h * 0.4,             # 치수 보조선 시작 간격
        "dimgap": txt_h * 0.3,             # 글자~치수선 간격
        "dimdec": 0,                       # 소수 자리수(정수)
        "dimtih": 0, "dimtoh": 0,          # 글자를 치수선과 정렬
        "dimtxsty": KFONT,                 # 치수 글자도 한글 폰트
        "dimtsz": 0,                       # 0이면 틱 대신 화살표 사용
        "dimblk": "",                      # 빈값 = 기본 채워진 화살표(closed filled)
        "dimsah": 0,                       # 양끝 화살표 동일 블록
        "dimclrd": 1, "dimclre": 1,        # 치수선/보조선 색(빨강)
    }

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
                    override=dim_override,
                    dxfattribs={"layer": "DIM"})
                dim.render()
            except Exception:  # noqa: BLE001 - 치수 실패해도 도면은 출력
                pass
        # 뷰 제목
        msp.add_text(view.name, height=txt_h * 1.1,
                     dxfattribs={"layer": "TEXT", "style": KFONT}).set_placement(
            (cursor, off_y + cv(y1 - y0) + txt_h * 1.5))
        for lb in view.labels:
            msp.add_text(lb.text, height=txt_h,
                         dxfattribs={"layer": "TEXT", "style": KFONT}).set_placement(P(lb.pos))
        cursor += cv(x1 - x0) + gap_u

    doc.saveas(path)
    return path
