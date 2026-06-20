"""제작도 시트(Fabrication Sheet) DXF — 023_cutting detail.pdf 형식.

한 장의 도면에 다음을 배치한다.
  - 상단: DESCRIPTION AND SHEAR LIST 표 + 우측 정보블록(FITTING I.D 등)
  - 좌하: 조립도(완성도) 1컷
  - 우하: CUTTING & BENDING DETAIL — 전개 조각(HEEL/THROAT/CHEEKS …)
  - 전체: 도면 테두리(프레임)

좌표는 모두 '종이좌표'(mm, A3 가로). 각 블록의 실제 형상은 칸에 맞게 축소·배치하고,
치수 문자는 축소와 무관하게 '실제 치수(mm)'를 표기한다(PDF 와 동일한 방식).
"""
from __future__ import annotations

import math
import re

import ezdxf
from ezdxf.enums import TextEntityAlignment

from ..core.pattern import Pattern
from ..core.drawing import AssemblyDrawing
from ..core.units import from_mm

# A3 가로 종이 + 여백(mm)
PW, PH = 420.0, 297.0
MARGIN = 8.0
TH_TITLE = 56.0          # 상단 표제부 높이
KFONT = "HANGEUL"

_STEEL_DENSITY = 7.85e-6  # kg/mm^3 (7850 kg/m^3)


# ---------------- 저수준 작도 헬퍼 ----------------
def _style(doc):
    if KFONT not in doc.styles:
        doc.styles.add(KFONT, font="malgun.ttf")
    for name, color in (("OUTLINE", 7), ("FOLD", 3), ("MARK", 30),
                         ("DIM", 1), ("TEXT", 2), ("FRAME", 7)):
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    if "DASHED" in doc.linetypes:
        doc.layers.get("FOLD").dxf.linetype = "DASHED"


def _rect(msp, x0, y0, x1, y1, layer="FRAME", lw=None):
    attr = {"layer": layer}
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
                       dxfattribs=attr)


def _text(msp, s, x, y, h, align=TextEntityAlignment.MIDDLE_LEFT, layer="TEXT"):
    t = msp.add_text(str(s), height=h,
                     dxfattribs={"layer": layer, "style": KFONT})
    t.set_placement((x, y), align=align)
    return t


def _arrow(msp, tip, ang, size, layer="DIM"):
    """tip 점에서 ang(rad) 방향으로 향하는 채워진 화살촉."""
    bx = tip[0] - size * math.cos(ang)
    by = tip[1] - size * math.sin(ang)
    w = size * 0.32
    px, py = -math.sin(ang) * w, math.cos(ang) * w
    msp.add_solid([tip, (bx + px, by + py), (bx - px, by - py), tip],
                  dxfattribs={"layer": layer})


def _hdim(msp, x1, x2, y, text, h, y_ext=None):
    """수평 치수. x1~x2 사이, y 위치 치수선. text=실제값 문자."""
    if abs(x2 - x1) < 1e-6:
        return
    a = h * 0.9
    if y_ext is not None:                       # 보조선
        for x in (x1, x2):
            msp.add_line((x, y_ext), (x, y + math.copysign(h * 0.4, y - y_ext)),
                         dxfattribs={"layer": "DIM"})
    msp.add_line((x1, y), (x2, y), dxfattribs={"layer": "DIM"})
    _arrow(msp, (x1, y), math.pi, a)            # 왼쪽 화살(오른쪽을 향해)
    _arrow(msp, (x2, y), 0.0, a)
    _text(msp, text, (x1 + x2) / 2, y + h * 0.7, h,
          TextEntityAlignment.BOTTOM_CENTER, "DIM")


def _vdim(msp, y1, y2, x, text, h, x_ext=None):
    if abs(y2 - y1) < 1e-6:
        return
    a = h * 0.9
    if x_ext is not None:
        for y in (y1, y2):
            msp.add_line((x_ext, y), (x + math.copysign(h * 0.4, x - x_ext), y),
                         dxfattribs={"layer": "DIM"})
    msp.add_line((x, y1), (x, y2), dxfattribs={"layer": "DIM"})
    _arrow(msp, (x, y1), -math.pi / 2, a)
    _arrow(msp, (x, y2), math.pi / 2, a)
    t = _text(msp, text, x + h * 0.7, (y1 + y2) / 2, h,
              TextEntityAlignment.BOTTOM_CENTER, "DIM")
    t.dxf.rotation = 90


def _fit(cbox, rect, pad):
    """content bbox -> rect 안에 종횡비 유지 배치하는 매핑 함수 P(pt) 반환."""
    cx0, cy0, cx1, cy1 = cbox
    cw, ch = max(cx1 - cx0, 1e-6), max(cy1 - cy0, 1e-6)
    rx0, ry0, rx1, ry1 = rect
    rw, rh = (rx1 - rx0) - 2 * pad, (ry1 - ry0) - 2 * pad
    s = min(rw / cw, rh / ch)
    ox = rx0 + pad + (rw - cw * s) / 2 - cx0 * s
    oy = ry0 + pad + (rh - ch * s) / 2 - cy0 * s

    def P(pt):
        return (pt[0] * s + ox, pt[1] * s + oy)
    return P, s


# ---------------- 부재 설명/치수 ----------------
def _desc(name: str) -> str:
    """패널 한글명에서 영문 부재명(대문자)을 뽑는다. 없으면 원본."""
    m = re.findall(r"[A-Za-z]+", name)
    return m[-1].upper() if m else name


def _desc_label(panel) -> str:
    """부재명(수량>1이면 복수형). 표/도형 라벨 공통."""
    d = _desc(panel.name)
    if panel.qty > 1 and not d.endswith("S"):
        d += "S"
    return d


def _poly_area(pts) -> float:
    a = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def _shear_dim(panel) -> str:
    x0, y0, x1, y1 = panel.bbox()
    return f"{x1 - x0:.0f} x {y1 - y0:.0f}"


# ---------------- 표제부 ----------------
def _title_block(msp, rect, pattern, meta):
    x0, y0, x1, y1 = rect
    h = 3.0
    _rect(msp, x0, y0, x1, y1, "FRAME")
    # 우측 정보블록 폭
    info_w = 92.0
    xi = x1 - info_w
    msp.add_line((xi, y0), (xi, y1), dxfattribs={"layer": "FRAME"})

    # --- 좌측: 제목 + 표 ---
    title_h = 11.0
    yt = y1 - title_h
    msp.add_line((x0, yt), (xi, yt), dxfattribs={"layer": "FRAME"})
    _text(msp, "DESCRIPTION AND SHEAR LIST", (x0 + xi) / 2, yt + title_h / 2,
          6.0, TextEntityAlignment.MIDDLE_CENTER)

    cols = [
        ("IDENTIFICATION NO.", 0.20),
        ("DUCT SIZE (IN)", 0.10),
        ("SHEAR DIMENSION (MM)", 0.15),
        ("Q'TY (PC)", 0.08),
        ("DESCRIPTION", 0.13),
        ("SEAM METHOD", 0.10),
        ("WELD METHOD", 0.10),
        ("REMARKS", 0.14),
    ]
    tw = xi - x0
    xs = [x0]
    for _, frac in cols:
        xs.append(xs[-1] + tw * frac)
    xs[-1] = xi
    # 헤더 행 + 데이터 행 높이
    rows_area_h = yt - y0
    n_data = max(len(pattern.panels), 1)
    hdr_h = rows_area_h / (n_data + 1) * 1.1
    row_h = (rows_area_h - hdr_h) / n_data
    # 세로선
    for x in xs:
        msp.add_line((x, y0), (x, yt), dxfattribs={"layer": "FRAME"})
    # 헤더 가로선
    yhr = yt - hdr_h
    msp.add_line((x0, yhr), (xi, yhr), dxfattribs={"layer": "FRAME"})
    for i, (label, _) in enumerate(cols):
        _text(msp, label, (xs[i] + xs[i + 1]) / 2, yt - hdr_h / 2, 2.1,
              TextEntityAlignment.MIDDLE_CENTER)
    # 데이터 행
    for r, panel in enumerate(pattern.panels):
        yr1 = yhr - r * row_h
        yr0 = yr1 - row_h
        if r > 0:
            msp.add_line((x0, yr1), (xi, yr1), dxfattribs={"layer": "FRAME"})
        cy = (yr0 + yr1) / 2
        vals = [
            meta.get("fitting_id", "") if r == 0 else "",
            meta.get("duct_size", "") if r == 0 else "",
            _shear_dim(panel),
            str(panel.qty),
            _desc_label(panel),
            "N/A", "N/A", "",
        ]
        for i, v in enumerate(vals):
            _text(msp, v, (xs[i] + xs[i + 1]) / 2, cy, 2.3,
                  TextEntityAlignment.MIDDLE_CENTER)

    # --- 우측 정보블록 ---
    weight = sum(_poly_area(p.outline) * p.qty for p in pattern.panels) \
        * meta.get("thickness_mm", 1.31) * _STEEL_DENSITY
    info = [
        ("FITTING I.D", meta.get("fitting_id", "-")),
        ("DETAIL NO.", meta.get("detail_no", "-")),
        ("MATERIAL", meta.get("material", "GALV. STEEL")),
        ("THICKNESS", meta.get("thickness", f"{meta.get('thickness_mm', 1.31):.3f}(mm)")),
        ("WEIGHT", f"{weight:.1f} (Kg)"),
    ]
    attach = ["ATTACHMENTS", "ACCES DOOR", "STIFFENER", "I&C TAP/HOLE"]
    n_info = len(info) + len(attach)
    rh = (y1 - y0) / n_info
    yk = y1
    kx = xi + info_w * 0.42
    for label, val in info:
        yk -= rh
        msp.add_line((xi, yk), (x1, yk), dxfattribs={"layer": "FRAME"})
        msp.add_line((kx, yk), (kx, yk + rh), dxfattribs={"layer": "FRAME"})
        _text(msp, label, xi + 1.5, yk + rh / 2, 2.1)
        _text(msp, val, (kx + x1) / 2, yk + rh / 2, 2.3,
              TextEntityAlignment.MIDDLE_CENTER)
    # ATTACHMENTS 헤더
    yk -= rh
    msp.add_line((xi, yk), (x1, yk), dxfattribs={"layer": "FRAME"})
    _text(msp, "ATTACHMENTS", (xi + x1) / 2, yk + rh / 2, 2.4,
          TextEntityAlignment.MIDDLE_CENTER)
    for label in attach[1:]:
        yk -= rh
        msp.add_line((xi, yk), (x1, yk), dxfattribs={"layer": "FRAME"})
        msp.add_line((kx, yk), (kx, yk + rh), dxfattribs={"layer": "FRAME"})
        _text(msp, label, xi + 1.5, yk + rh / 2, 2.1)


# ---------------- 조립도(완성도) ----------------
def _flatten_assembly(drawing: AssemblyDrawing, gap_frac=0.12):
    """완성도 뷰들을 한 좌표공간에 가로로 나열해 평탄화."""
    polys, circs, folds, labels = [], [], [], []
    cursor = 0.0
    span = 0.0
    for v in drawing.views:
        x0, y0, x1, y1 = v.bbox()
        span = max(span, x1 - x0, y1 - y0)
    gap = max(span * gap_frac, 20.0)
    for v in drawing.views:
        x0, y0, x1, y1 = v.bbox()
        ox = cursor - x0
        for pl in v.polylines:
            polys.append([(p[0] + ox, p[1]) for p in pl])
        for cx, cy, r in v.circles:
            circs.append((cx + ox, cy, r))
        for a, b in v.fold_lines:
            folds.append(((a[0] + ox, a[1]), (b[0] + ox, b[1])))
        for lb in v.labels:
            labels.append((lb.pos[0] + ox, lb.pos[1], lb.text))
        cursor += (x1 - x0) + gap
    xs, ys = [], []
    for pl in polys:
        for x, y in pl:
            xs.append(x); ys.append(y)
    for cx, cy, r in circs:
        xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
    if not xs:
        return None
    cbox = (min(xs), min(ys), max(xs), max(ys))
    return polys, circs, folds, labels, cbox


def _assembly_block(msp, rect, drawing):
    x0, y0, x1, y1 = rect
    _rect(msp, x0, y0, x1, y1, "FRAME")
    _text(msp, drawing.shape_name, x0 + 4, y1 - 6, 4.5)
    flat = _flatten_assembly(drawing)
    if flat is None:
        return
    polys, circs, folds, labels, cbox = flat
    P, s = _fit(cbox, (x0, y0, x1, y1 - 10), pad=10.0)
    import numpy as np
    for pl in polys:
        msp.add_lwpolyline([P(p) for p in pl], dxfattribs={"layer": "OUTLINE"})
    for cx, cy, r in circs:
        msp.add_circle(P((cx, cy)), r * s, dxfattribs={"layer": "OUTLINE"})
    for a, b in folds:
        msp.add_line(P(a), P(b), dxfattribs={"layer": "FOLD"})
    for lx, ly, txt in labels:
        _text(msp, txt, *P((lx, ly)), 3.0, TextEntityAlignment.MIDDLE_CENTER)


# ---------------- 전개 조각(CUTTING & BENDING) ----------------
def _panel_block(msp, panel, rect):
    """패널 1개를 rect 칸에 배치 + 라벨 + 치수(실제 mm)."""
    x0, y0, x1, y1 = rect
    px0, py0, px1, py1 = panel.bbox()
    w, h = px1 - px0, py1 - py0

    # 라벨 칸(좌측 28%) / 도형 칸(우측)
    lab_w = (x1 - x0) * 0.26
    gx0 = x0 + lab_w
    _text(msp, _desc_label(panel), x0 + lab_w / 2, (y0 + y1) / 2, 7.0,
          TextEntityAlignment.MIDDLE_CENTER)
    msp.add_line((gx0, y0), (gx0, y1), dxfattribs={"layer": "FRAME"})

    # 도형은 치수 여백을 두고 배치. 외형은 닫아 그려 좌변(세로선)이 빠지지 않게 한다.
    P, s = _fit((px0, py0, px1, py1), (gx0, y0, x1, y1), pad=15.0)
    msp.add_lwpolyline([P(p) for p in panel.outline],
                       close=True, dxfattribs={"layer": "OUTLINE"})
    for a, b in panel.fold_lines:
        msp.add_line(P(a), P(b), dxfattribs={"layer": "FOLD"})
    for a, b in panel.mark_lines:
        msp.add_line(P(a), P(b), dxfattribs={"layer": "MARK"})

    dh = 3.0
    # 외곽 좌표(종이) 범위
    sx0, sy0 = P((px0, py0))
    sx1, sy1 = P((px1, py1))
    # 상단: 전체 폭
    _hdim(msp, sx0, sx1, sy1 + 8, f"{w:.0f}", dh, y_ext=sy1)
    # 우측: 전체 높이
    _vdim(msp, sy0, sy1, sx1 + 8, f"{h:.0f}", dh, x_ext=sx1)

    # 하단: 절곡/경계선 x 위치로 구간 분할 치수
    xset = {px0, px1}
    for a, b in list(panel.fold_lines) + list(panel.mark_lines):
        if abs(a[0] - b[0]) < 1e-6 and py0 - 1 <= a[1] <= py1 + 1:  # 수직선
            xset.add(a[0])
    xs = sorted(v for v in xset if px0 - 1e-6 <= v <= px1 + 1e-6)
    if len(xs) > 2:
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            pa = P((xa, py0))[0]
            pb = P((xb, py0))[0]
            _hdim(msp, pa, pb, sy0 - 8, f"{xb - xa:.0f}", dh, y_ext=sy0)


def _cutting_block(msp, rect, pattern):
    x0, y0, x1, y1 = rect
    _rect(msp, x0, y0, x1, y1, "FRAME")
    hdr_h = 9.0
    yh = y1 - hdr_h
    msp.add_line((x0, yh), (x1, yh), dxfattribs={"layer": "FRAME"})
    _text(msp, "CUTTING & BENDING DETAIL(mm)", (x0 + x1) / 2, yh + hdr_h / 2,
          5.0, TextEntityAlignment.MIDDLE_CENTER)

    n = max(len(pattern.panels), 1)
    cell_h = (yh - y0) / n
    for i, panel in enumerate(pattern.panels):
        cy1 = yh - i * cell_h
        cy0 = cy1 - cell_h
        if i > 0:
            msp.add_line((x0, cy1), (x1, cy1), dxfattribs={"layer": "FRAME"})
        _panel_block(msp, panel, (x0, cy0, x1, cy1))


# ---------------- 시트 ----------------
def export_sheet(pattern: Pattern, drawing: AssemblyDrawing, path: str,
                 meta: dict | None = None) -> str:
    meta = dict(meta or {})
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    _style(doc)
    msp = doc.modelspace()

    ix0, iy0, ix1, iy1 = MARGIN, MARGIN, PW - MARGIN, PH - MARGIN
    # 외곽 프레임(이중선)
    _rect(msp, 0, 0, PW, PH, "FRAME")
    _rect(msp, ix0, iy0, ix1, iy1, "FRAME")

    # 상단 표제부
    title_rect = (ix0, iy1 - TH_TITLE, ix1, iy1)
    _title_block(msp, title_rect, pattern, meta)

    # 본문: 좌(조립도) / 우(전개)
    body_top = iy1 - TH_TITLE
    split = ix0 + (ix1 - ix0) * 0.36
    if drawing is not None and drawing.views:
        _assembly_block(msp, (ix0, iy0, split, body_top), drawing)
        cut_x0 = split
    else:
        cut_x0 = ix0
    _cutting_block(msp, (cut_x0, iy0, ix1, body_top), pattern)

    doc.saveas(path)
    return path
