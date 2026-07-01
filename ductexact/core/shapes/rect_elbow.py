"""사각 엘보(곡관) 전개: 측판 2장 + 목/등 외피 스트립."""
from __future__ import annotations

import math

from .. import allowances as al
from .. import geometry as g
from ..pattern import Pattern, Panel
from .base import Shape, ParamSpec, CommonSettings


def cheek_outline(Rt: float, Rh: float, theta: float, leg0: float, legT: float,
                  n: int = 48, end: float = 0.0):
    """측판(cheek) 외형: 동심 원호(Rt,Rh) + 양단 직관[+단부여유 end] 탭.

    입구단(각 0)은 −y 방향, 출구단(각 θ)은 접선 방향으로 직관이 뻗는다.
    leg0=입구단 직관 길이, legT=출구단 직관 길이(양끝 다를 수 있음).
    완성도(프로파일, end=0)와 전개도(end 반영)가 공유.
    """
    ll0 = leg0 + end                     # 입구단 직관 + 단부 플랜지 여유
    llT = legT + end                     # 출구단 직관 + 단부 플랜지 여유
    ct, st = math.cos(theta), math.sin(theta)
    tt = (-st, ct)                       # θ단 바깥쪽 접선
    inner = g.arc_points(0, 0, Rt, 0, theta, n)
    outer = g.arc_points(0, 0, Rh, theta, 0, n)
    P_inT, P_outT = inner[-1], outer[0]
    in0_leg = (Rt, -ll0)
    out0_leg = (Rh, -ll0)
    inT_leg = (P_inT[0] + llT * tt[0], P_inT[1] + llT * tt[1])
    outT_leg = (P_outT[0] + llT * tt[0], P_outT[1] + llT * tt[1])
    return ([in0_leg] + inner + [inT_leg, outT_leg]
            + outer + [out0_leg, in0_leg])


class RectElbow(Shape):
    key = "rect_elbow"
    name = "사각 엘보(곡관)"
    description = "반경형 사각 엘보. 측판(cheek) 2장 + 목(throat)/등(heel) 외피."

    params = [
        ParamSpec("W", "가로 W(곡면방향)", "length", 300, "mm",
                  help="목→등 방향 치수. 등반경 = 목반경 + W"),
        ParamSpec("H", "세로 H(외피 폭)", "length", 250, "mm"),
        ParamSpec("Rt", "목반경 Rt", "length", 100, "mm"),
        ParamSpec("angle", "각도 θ", "angle", 90, "deg", minimum=1, maximum=180),
        ParamSpec("leg1", "입구단 직관 L1", "length", 50, "mm",
                  help="입구쪽 직선부 길이(절곡선까지). 0이면 직관 없음."),
        ParamSpec("leg2", "출구단 직관 L2", "length", 50, "mm",
                  help="출구쪽 직선부 길이(절곡선까지). 0이면 직관 없음."),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        W = cfg.to_neutral(p["W"])
        H = cfg.to_neutral(p["H"])
        Rt = p["Rt"]
        theta = math.radians(p["angle"])
        leg1 = p.get("leg1", 50.0)      # 입구단 직관
        leg2 = p.get("leg2", 50.0)      # 출구단 직관
        Rh = Rt + W
        seam = al.seam_allowance(cfg.seam, cfg.seam_table)   # 외피↔측판 락심(폭 방향)
        end = al.end_allowance(cfg.joint, cfg.end_table)     # 단부연결(길이 양끝)

        # --- 측판(CHEEK): 동심 원호 + 양단 직관(+단부여유) ---
        cheek = cheek_outline(Rt, Rh, theta, leg1, leg2, end=end)
        x0, y0, x1, y1 = g.bbox(cheek)
        cheek = g.translate(cheek, -x0, -y0)
        # 측판 단부 여유 경계(직관/단부 플랜지 경계) — 여유 경계선
        cheek_marks = []
        if end > 0:
            ct, st = math.cos(theta), math.sin(theta)
            tt = (-st, ct)
            P_inT, P_outT = (Rt * ct, Rt * st), (Rh * ct, Rh * st)
            segs = [((Rt, -leg1), (Rh, -leg1)),
                    ((P_inT[0] + leg2 * tt[0], P_inT[1] + leg2 * tt[1]),
                     (P_outT[0] + leg2 * tt[0], P_outT[1] + leg2 * tt[1]))]
            cheek_marks = [((a[0] - x0, a[1] - y0), (b[0] - x0, b[1] - y0))
                           for a, b in segs]

        # --- 외피 wrap: [end|leg|호|leg|end] 길이 × (H+seam) 폭 ---
        throat_len = Rt * theta
        heel_len = Rh * theta

        def wrap(arc_len: float, name: str, tag: str) -> Panel:
            total = 2 * end + leg1 + leg2 + arc_len
            Hdev = H + seam
            outline = [(0, 0), (total, 0), (total, Hdev), (0, Hdev)]
            folds = []
            xa, xb = end + leg1, end + leg1 + arc_len        # 직관/곡면 경계(절곡)
            folds += [((xa, 0), (xa, Hdev)), ((xb, 0), (xb, Hdev))]
            marks = []
            if end > 0:                                      # 단부 여유 경계
                marks += [((end, 0), (end, Hdev)),
                          ((total - end, 0), (total - end, Hdev))]
            if seam > 0:                                     # 심 경계(폭 방향)
                marks.append(((0, H), (total, H)))
            return Panel(name, outline, qty=1, fold_lines=folds, mark_lines=marks,
                         texts=[(total / 2, Hdev / 2, f"{tag}  L={total:.0f}")])

        # 측판 곡선 = 동심 원호(목/등). 중심은 원점→정규화로 (-x0,-y0) 이동.
        deg = math.degrees(theta)
        cheek_curves = [
            {"kind": "arc", "name": "목 원호 Rt", "cx": -x0, "cy": -y0,
             "r": Rt, "a0": 0.0, "a1": deg},
            {"kind": "arc", "name": "등 원호 Rh", "cx": -x0, "cy": -y0,
             "r": Rh, "a0": 0.0, "a1": deg},
        ]

        pat = Pattern(self.name)
        pat.add_panel(Panel("측판 Cheek", cheek, qty=2, mark_lines=cheek_marks,
                            curves=cheek_curves,
                            texts=[((x1 - x0) * 0.55, (y1 - y0) * 0.45,
                                    "CHEEK x2")]))
        pat.add_panel(wrap(throat_len, "목 외피 Throat", "THROAT"))
        pat.add_panel(wrap(heel_len, "등 외피 Heel", "HEEL"))

        pat.add_row(항목="목반경 Rt", 값=round(Rt, 1), 단위="mm")
        pat.add_row(항목="등반경 Rh", 값=round(Rh, 1), 단위="mm")
        pat.add_row(항목="목 호길이", 값=round(throat_len, 1), 단위="mm")
        pat.add_row(항목="등 호길이", 값=round(heel_len, 1), 단위="mm")
        pat.add_row(항목="외피 폭(H+심)", 값=round(H + seam, 1), 단위="mm")
        pat.add_row(항목="입구단 직관 L1", 값=round(leg1, 1), 단위="mm")
        pat.add_row(항목="출구단 직관 L2", 값=round(leg2, 1), 단위="mm")
        pat.add_row(항목="심 여유", 값=round(seam, 1), 단위="mm")
        pat.add_row(항목="단부 여유(편측)", 값=round(end, 1), 단위="mm")
        pat.add_row(항목="HEEL 전개길이", 값=round(2 * end + leg1 + leg2 + heel_len, 1), 단위="mm")
        pat.add_row(항목="THROAT 전개길이", 값=round(2 * end + leg1 + leg2 + throat_len, 1), 단위="mm")
        pat.add_row(항목="측판 매수", 값=2, 단위="EA")
        pat.notes.append("외피 폭에 심(측판 락심), 길이 양끝에 단부여유 반영. 절곡선=경계.")
        pat.notes.append(f"각도 {p['angle']:g}° / 직관 L1={leg1:g} L2={leg2:g} / 심:{cfg.seam} / "
                         f"단부:{cfg.joint} / {cfg.gauge}GA")
        return pat
