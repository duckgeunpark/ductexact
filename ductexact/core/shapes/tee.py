"""티/와이(분기) 전개.

원형 분기: 본관(반경 R)에 분기관(반경 r)이 각도 α로 만나는 표준 전개.
- 분기관 새들(saddle) 컷 전개
- 본관에 뚫을 구멍(hole) 템플릿 전개
사각 티: 분기관(사각 직관 전개) + 본관 사각 구멍 템플릿.
"""
from __future__ import annotations

import math

from .. import allowances as al
from ..pattern import Pattern, Panel
from .base import Shape, ParamSpec, CommonSettings


def _branch_axial_dist(phi: float, R: float, r: float, alpha: float) -> float:
    """분기 둘레각 phi 에서 본관 표면까지의 분기축 거리 s(phi).

    본관축=X, 표면 y^2+z^2=R^2. 분기축은 XZ평면에서 X와 alpha 각.
    """
    A = r * math.cos(phi)               # y 성분
    B = r * math.sin(phi) * math.cos(alpha)
    disc = R * R - A * A
    if disc < 0:
        disc = 0.0
    return (-B + math.sqrt(disc)) / math.sin(alpha)


def _branch_point(phi: float, s: float, r: float, alpha: float):
    """분기 벽면 3D 점 (본관 좌표계)."""
    x = s * math.cos(alpha) - r * math.sin(phi) * math.sin(alpha)
    y = r * math.cos(phi)
    z = s * math.sin(alpha) + r * math.sin(phi) * math.cos(alpha)
    return x, y, z


class RoundTee(Shape):
    key = "round_tee"
    name = "원형 티/와이"
    description = "원형 본관에 원형 분기. 분기관 새들 전개 + 본관 구멍 템플릿."

    params = [
        ParamSpec("Dm", "본관 지름 Dm", "length", 400, "mm"),
        ParamSpec("Db", "분기 지름 Db", "length", 250, "mm"),
        ParamSpec("Lb", "분기 길이 Lb", "length", 300, "mm"),
        ParamSpec("angle", "분기 각도 α", "angle", 90, "deg", minimum=15, maximum=90,
                  help="90°=티, 그 외=와이/래터럴"),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        Dm = cfg.to_neutral(p["Dm"])
        Db = cfg.to_neutral(p["Db"])
        Lb = p["Lb"]
        alpha = math.radians(p["angle"])
        R, r = Dm / 2, Db / 2
        if r >= R:
            r = R * 0.999  # 분기가 본관보다 크면 클램프

        seam = al.seam_allowance(cfg.seam, cfg.seam_table)
        end = al.end_allowance(cfg.joint, cfg.end_table)

        n = 72
        # 분기축 거리 s(phi)
        s_vals = [_branch_axial_dist(2 * math.pi * i / n, R, r, alpha)
                  for i in range(n + 1)]
        s_min = min(s_vals)
        top = Lb + max(s_vals)  # 분기 전체 길이(가장 깊은 컷 기준 윗변 평탄)
        top_y = top - s_min     # 자유단(분기 끝) 위치
        free_y = top_y + end    # 단부 여유 포함 윗변

        # --- 분기관 새들 전개 (폭 = 원주 + 심) ---
        circ = math.pi * Db
        dev_w = circ + seam
        bottom = [(circ * i / n, s_vals[i] - s_min) for i in range(n + 1)]
        y_seam = s_vals[n] - s_min   # 원주 끝(=시작) 높이 → 심 strip 밑변
        outline = [(0.0, free_y)] + bottom
        if seam > 0:
            outline += [(dev_w, y_seam), (dev_w, free_y)]
        else:
            outline += [(circ, free_y)]
        marks = []
        if seam > 0:
            marks.append(((circ, y_seam), (circ, free_y)))   # 심 경계
        if end > 0:
            marks.append(((0.0, top_y), (dev_w, top_y)))     # 단부 여유 경계
        # 새들 밑변은 원통-원통 교선(원호 아님, 반경 없음) → 좌표법 공식 명시
        saddle = {"kind": "formula", "name": "새들 컷(밑변)",
                  "expr": "원통교선: s(φ)=(√(R²−r²cos²φ) − r·sinφ·cosα)/sinα, "
                          "x=원주·φ/2π",
                  "params": {"본관R": R, "분기r": r,
                             "각도α": f"{p['angle']:g}°", "원주": circ}}
        branch = Panel("분기관 Branch", outline, qty=1, mark_lines=marks,
                       curves=[saddle],
                       texts=[(circ / 2, top_y / 2, f"Ø{Db:g} L={Lb:g}")])

        # --- 본관 구멍 템플릿 (본관 표면 전개: U=R·ψ, V=x) ---
        hole_pts = []
        for i in range(n + 1):
            phi = 2 * math.pi * i / n
            s = s_vals[i]
            x, y, z = _branch_point(phi, s, r, alpha)
            psi = math.atan2(z, y)
            hole_pts.append((R * psi, x))
        # 정규화
        xs = [q[0] for q in hole_pts]
        ys = [q[1] for q in hole_pts]
        ox, oy = min(xs), min(ys)
        hole = Panel("본관 구멍 Hole", [(qx - ox, qy - oy) for qx, qy in hole_pts],
                     qty=1, texts=[(0, 0, "본관에 뚫을 구멍")])

        pat = Pattern(self.name)
        pat.add_panel(branch)
        pat.add_panel(hole)
        pat.add_row(항목="본관 Ø", 값=round(Dm, 1), 단위="mm")
        pat.add_row(항목="분기 Ø", 값=round(Db, 1), 단위="mm")
        pat.add_row(항목="분기 원주", 값=round(circ, 1), 단위="mm")
        pat.add_row(항목="분기 전개 폭", 값=round(dev_w, 1), 단위="mm")
        pat.add_row(항목="새들 최대 깊이", 값=round(max(s_vals) - s_min, 1), 단위="mm")
        pat.add_row(항목="심 여유", 값=round(seam, 1), 단위="mm")
        pat.add_row(항목="단부 여유(자유단)", 값=round(end, 1), 단위="mm")
        pat.add_row(항목="분기 각도", 값=round(p["angle"], 1), 단위="deg")
        pat.notes.append("새들 곡선 = 원통-원통 교선. 본관 구멍은 안쪽에서 마킹.")
        pat.notes.append("심은 자유단 쪽 한 변에 부여, 새들 밑변은 본관에 맞춰 절단.")
        pat.notes.append(f"{p['angle']:g}° 분기 / 심:{cfg.seam} / 단부:{cfg.joint} / {cfg.gauge}GA")
        return pat


class RectTee(Shape):
    key = "rect_tee"
    name = "사각 티"
    description = "사각 본관에 사각 분기(90°). 분기관 전개 + 본관 직사각 구멍."

    params = [
        ParamSpec("Wm", "본관 가로 Wm", "length", 400, "mm"),
        ParamSpec("Hm", "본관 세로 Hm", "length", 300, "mm"),
        ParamSpec("Wb", "분기 가로 Wb", "length", 250, "mm"),
        ParamSpec("Hb", "분기 세로 Hb", "length", 200, "mm"),
        ParamSpec("Lb", "분기 길이 Lb", "length", 300, "mm"),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        Wb = cfg.to_neutral(p["Wb"])
        Hb = cfg.to_neutral(p["Hb"])
        Lb = p["Lb"]
        seam = al.seam_allowance(cfg.seam, cfg.seam_table)
        end = al.end_allowance(cfg.joint, cfg.end_table)

        # 분기관: 사각 직관 전개 (폭 = 둘레 + 심, 길이 = Lb + 자유단 단부 여유)
        dev_w = 2 * (Wb + Hb) + seam
        dev_l = Lb + end
        folds = [((x, 0), (x, dev_l)) for x in (Wb, Wb + Hb, 2 * Wb + Hb)]
        marks = []
        if seam > 0:
            marks.append(((2 * (Wb + Hb), 0), (2 * (Wb + Hb), dev_l)))  # 심 경계
        if end > 0:
            marks.append(((0, Lb), (dev_w, Lb)))                       # 단부 여유 경계
        body = Panel("분기관 Branch",
                     [(0, 0), (dev_w, 0), (dev_w, dev_l), (0, dev_l)],
                     qty=1, fold_lines=folds, mark_lines=marks,
                     texts=[(dev_w / 2, dev_l / 2, f"{Wb:g}x{Hb:g} L={Lb:g}")])
        # 본관 구멍: 분기 단면 직사각형(평면 본관 가정)
        hole = Panel("본관 구멍 Hole", [(0, 0), (Wb, 0), (Wb, Hb), (0, Hb)], qty=1,
                     texts=[(Wb / 2, Hb / 2, "본관 구멍")])

        pat = Pattern(self.name)
        pat.add_panel(body)
        pat.add_panel(hole)
        pat.add_row(항목="분기 전개 폭", 값=round(dev_w, 1), 단위="mm")
        pat.add_row(항목="분기 길이", 값=round(Lb, 1), 단위="mm")
        pat.add_row(항목="심 여유", 값=round(seam, 1), 단위="mm")
        pat.add_row(항목="단부 여유(자유단)", 값=round(end, 1), 단위="mm")
        pat.add_row(항목="본관 구멍", 값=f"{Wb:g}x{Hb:g}", 단위="mm")
        pat.notes.append("평면 본관 가정. 곡면 본관이면 구멍은 새들 보정 필요.")
        pat.notes.append(f"심:{cfg.seam} / 단부:{cfg.joint} / {cfg.gauge}GA")
        return pat
