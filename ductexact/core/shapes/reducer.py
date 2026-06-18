"""리듀서/천이 전개: 원형↔원형(콘), 사각↔원형(삼각분할), 사각↔사각(4면)."""
from __future__ import annotations

import math

from .. import allowances as al
from .. import geometry as g
from ..pattern import Pattern, Panel
from .base import Shape, ParamSpec, CommonSettings


def _cone_frustum(D1: float, D2: float, L: float) -> tuple[list, float, float, float]:
    """동심 원형 콘 전개 = 부채꼴. 반환(outline, 큰반경, 작은반경, 각도deg)."""
    R1, R2 = D1 / 2, D2 / 2
    if abs(R1 - R2) < 1e-9:        # 사실상 직관
        R2 = R1 - 1e-6
    big, small = (R1, R2) if R1 > R2 else (R2, R1)
    slant = math.hypot(L, big - small)
    Rb = slant * big / (big - small)      # 큰 호 반경
    Rs = Rb - slant                       # 작은 호 반경
    phi = 2 * math.pi * big / Rb          # 부채꼴 각도(rad)
    inner = g.arc_points(0, 0, Rs, 0, phi, 64)
    outer = g.arc_points(0, 0, Rb, phi, 0, 64)
    outline = inner + outer
    x0, y0, _, _ = g.bbox(outline)
    outline = g.translate(outline, -x0, -y0)
    return outline, Rb, Rs, math.degrees(phi)


def _square_to_round(W: float, H: float, D: float, L: float, k: int = 6) -> list:
    """동심 사각↔원형 표준 전개를 좌/우 2조각(각 ~180° 부채꼴)으로.

    4개 평면삼각형(각 변→해당 변의 접점) + 4개 코너 콘(코너→원 1/4호).
    한 조각으로 펼치면 360° 닫힌 띠가 되어 시접에서 자기교차하므로,
    변 중앙(접점 방향)을 심선으로 삼아 반씩 나눈다.  반환: [Panel, Panel].
    """
    r = D / 2
    c0 = (-W / 2, -H / 2, 0.0)
    c1 = (W / 2, -H / 2, 0.0)
    c2 = (W / 2, H / 2, 0.0)
    c3 = (-W / 2, H / 2, 0.0)
    mid0 = (0.0, -H / 2, 0.0)     # 아랫변 중앙(심)
    mid2 = (0.0, H / 2, 0.0)      # 윗변 중앙(심)
    ang = {"M0": -math.pi / 2, "M1": 0.0, "M2": math.pi / 2, "M3": math.pi}

    def circ(a):
        return (r * math.cos(a), r * math.sin(a), L)

    def cone(bottom_pt, a0, a1, top, bot):
        if a1 <= a0:
            a1 += 2 * math.pi
        for s in range(1, k + 1):
            top.append(circ(a0 + (a1 - a0) * s / k))
            bot.append(bottom_pt)

    def tri(p_from, p_to, apex_a, top, bot):
        m = circ(apex_a)
        top.append(m); bot.append(p_from)
        top.append(m); bot.append(p_to)

    def half(seq):
        top: list = []
        bot: list = []
        seq(top, bot)
        outline = g.triangulate_strip(top, bot, closed=False)
        x0, y0, _, _ = g.bbox(outline)
        return g.translate(outline, -x0, -y0)

    # A: mid0 → (+X쪽) → mid2
    def seqA(top, bot):
        tri(mid0, c1, ang["M0"], top, bot)
        cone(c1, ang["M0"], ang["M1"], top, bot)
        tri(c1, c2, ang["M1"], top, bot)
        cone(c2, ang["M1"], ang["M2"], top, bot)
        tri(c2, mid2, ang["M2"], top, bot)

    # B: mid2 → (−X쪽) → mid0
    def seqB(top, bot):
        tri(mid2, c3, ang["M2"], top, bot)
        cone(c3, ang["M2"], ang["M3"], top, bot)
        tri(c3, c0, ang["M3"], top, bot)
        cone(c0, ang["M3"], ang["M0"], top, bot)
        tri(c0, mid0, ang["M0"], top, bot)

    return [half(seqA), half(seqB)]


def _rect_to_rect(W1, H1, W2, H2, L) -> list[Panel]:
    """동심 사각→사각: 4면을 사다리꼴로 근사 전개(각 면 평면 가정)."""
    panels = []
    # 폭 방향 면(앞/뒤): 밑변 W1, 윗변 W2, 높이=면의 실길이
    slant_w = math.hypot(L, (H1 - H2) / 2)
    front = [(-W1 / 2, 0), (W1 / 2, 0), (W2 / 2, slant_w), (-W2 / 2, slant_w)]
    front = g.translate(front, W1 / 2, 0)
    panels.append(Panel("앞/뒤면 (W면)", front, qty=2))
    # 높이 방향 면(좌/우): 밑변 H1, 윗변 H2
    slant_h = math.hypot(L, (W1 - W2) / 2)
    side = [(-H1 / 2, 0), (H1 / 2, 0), (H2 / 2, slant_h), (-H2 / 2, slant_h)]
    side = g.translate(side, H1 / 2, 0)
    panels.append(Panel("좌/우면 (H면)", side, qty=2))
    return panels


class Reducer(Shape):
    key = "reducer"
    name = "리듀서/천이"
    description = "원형↔원형(콘), 사각↔원형(삼각분할), 사각↔사각(4면)."

    params = [
        ParamSpec("kind", "종류", "choice",
                  choices=["원형→원형", "사각→원형", "원형→사각", "사각→사각"]),
        ParamSpec("D1", "입구 지름/가로 W1", "length", 400, "mm"),
        ParamSpec("H1", "입구 세로 H1(사각만)", "length", 300, "mm"),
        ParamSpec("D2", "출구 지름/가로 W2", "length", 250, "mm"),
        ParamSpec("H2", "출구 세로 H2(사각만)", "length", 200, "mm"),
        ParamSpec("L", "길이 L", "length", 300, "mm"),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        kind = p.get("kind", "원형→원형")
        L = p["L"]
        D1 = cfg.to_neutral(p["D1"])
        H1 = cfg.to_neutral(p["H1"])
        D2 = cfg.to_neutral(p["D2"])
        H2 = cfg.to_neutral(p["H2"])
        p = {**p, "D1": D1, "H1": H1, "D2": D2, "H2": H2}
        seam = al.seam_allowance(cfg.seam, cfg.seam_table)
        end = al.end_allowance(cfg.joint, cfg.end_table)
        pat = Pattern(self.name)

        if kind == "원형→원형":
            outline, Rb, Rs, phi = _cone_frustum(p["D1"], p["D2"], L)
            pat.add_panel(Panel("콘 전개 Cone", outline, qty=1))
            pat.add_row(항목="큰 호 반경", 값=round(Rb, 1), 단위="mm")
            pat.add_row(항목="작은 호 반경", 값=round(Rs, 1), 단위="mm")
            pat.add_row(항목="부채꼴 각도", 값=round(phi, 2), 단위="deg")
        elif kind in ("사각→원형", "원형→사각"):
            # 물리적으로 동일 부재 → 전개 동일. 사각=(Wsq,Hsq), 원형=Dr.
            if kind == "사각→원형":
                Wsq, Hsq, Dr = p["D1"], p["H1"], p["D2"]
                in_txt, out_txt = f"{Wsq:g}x{Hsq:g}", f"Ø{Dr:g}"
            else:  # 원형→사각
                Dr, Wsq, Hsq = p["D1"], p["D2"], p["H2"]
                in_txt, out_txt = f"Ø{Dr:g}", f"{Wsq:g}x{Hsq:g}"
            halfA, halfB = _square_to_round(Wsq, Hsq, Dr, L)
            pat.add_panel(Panel("전개 A (절반)", halfA, qty=1,
                                texts=[(0, 0, "HALF A")]))
            pat.add_panel(Panel("전개 B (절반)", halfB, qty=1,
                                texts=[(0, 0, "HALF B")]))
            pat.add_row(항목="입구", 값=in_txt, 단위="mm")
            pat.add_row(항목="출구", 값=out_txt, 단위="mm")
            pat.add_row(항목="조각", 값="2조각(변 중앙 심)", 단위="EA")
            pat.notes.append("동심 삼각분할. 변 중앙을 심선으로 2조각 분할(자기교차 방지).")
            pat.notes.append("편심은 후속 지원.")
        else:  # 사각→사각
            for panel in _rect_to_rect(p["D1"], p["H1"], p["D2"], p["H2"], L):
                pat.add_panel(panel)
            pat.add_row(항목="입구", 값=f"{p['D1']:g}x{p['H1']:g}", 단위="mm")
            pat.add_row(항목="출구", 값=f"{p['D2']:g}x{p['H2']:g}", 단위="mm")
            pat.notes.append("각 면 평면 가정(근사). 정밀 전개는 삼각분할 후속.")

        pat.add_row(항목="길이 L", 값=round(L, 1), 단위="mm")
        pat.add_row(항목="심 여유", 값=round(seam, 1), 단위="mm")
        pat.add_row(항목="단부 여유(편측)", 값=round(end, 1), 단위="mm")
        pat.notes.append("심/단부 여유 값은 전개 가장자리에 별도 부가(절단선 = 정미치수).")
        pat.notes.append(f"{kind} / 심:{cfg.seam} / 단부:{cfg.joint} / {cfg.gauge}GA")
        return pat
