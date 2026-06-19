"""원형 엘보(새우관/gored elbow) 전개.

n조각 엘보: 양 끝 1/2 조각 2개 + 중간 온조각 (n-2)개.
조인트 수 = n-1, 조인트당 꺾임 β = θ/(n-1), 컷각 α = β/2.
원통을 평면 전개하면 미터 컷은 사인곡선: y = c + r·tan(α)·cos(φ).
"""
from __future__ import annotations

import math

from .. import allowances as al
from ..pattern import Pattern, Panel
from .base import Shape, ParamSpec, CommonSettings


def _gore_outline(r: float, half_len: float, a_bottom: float, a_top: float,
                  n: int = 72, seam: float = 0.0, end_bottom: float = 0.0):
    """전개 폭 = 원주(2πr)[+심].  하단/상단 미터곡선 진폭 a_*.

    half_len: 중심선 절반 축길이.  a=0 이면 평평한 끝(끝조각의 직선단).
    seam: 우측 모서리에 더하는 길이방향 락심 평판 폭.
    end_bottom: 평평한 하단(덕트 연결단)에 더하는 단부 여유.
    반환: (outline, seam_fold_segment | None)
    """
    circ = 2 * math.pi * r
    top: list[tuple[float, float]] = []
    bot: list[tuple[float, float]] = []
    for i in range(n + 1):
        phi = 2 * math.pi * i / n
        x = circ * i / n
        top.append((x, half_len + a_top * math.cos(phi)))
        bot.append((x, -half_len - end_bottom - a_bottom * math.cos(phi)))
    fold = None
    if seam > 0:
        ty, by = top[-1][1], bot[-1][1]      # 우측 모서리(x=circ) 상/하단
        strip = [(circ + seam, ty), (circ + seam, by)]
        outline = top + strip + list(reversed(bot))
        fold = ((circ, by), (circ, ty))
    else:
        outline = top + list(reversed(bot))
    return outline, fold


class RoundElbow(Shape):
    key = "round_elbow"
    name = "원형 엘보(새우관)"
    description = "n조각 분할 원형 엘보. 각 조각 사인곡선 전개."

    params = [
        ParamSpec("D", "지름 D", "length", 300, "mm"),
        ParamSpec("R", "중심선 반경 R", "length", 450, "mm"),
        ParamSpec("angle", "각도 θ", "angle", 90, "deg", minimum=1, maximum=180),
        ParamSpec("n", "분할수 n", "int", 5, minimum=2, maximum=20,
                  help="끝조각 2 + 중간조각(n-2). 90°는 보통 5."),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        D = cfg.to_neutral(p["D"])
        R = p["R"]
        theta = math.radians(p["angle"])
        n = int(p["n"])
        r = D / 2

        seam = al.seam_allowance(cfg.seam, cfg.seam_table)   # 길이방향 락심
        end = al.end_allowance(cfg.joint, cfg.end_table)     # 끝조각 덕트 연결단

        beta = theta / (n - 1)          # 조인트당 꺾임
        alpha = beta / 2                # 컷각
        a = r * math.tan(alpha)         # 미터 사인곡선 진폭

        end_half = R * beta / 2 / 2     # 끝조각 축길이 절반(끝조각=중간의 절반 길이)
        mid_half = R * beta / 2         # 중간조각 축길이 절반

        pat = Pattern(self.name)
        warn = mid_half - a
        # 끝조각: 한쪽 평평(a_bottom=0, 덕트 연결단→단부여유), 한쪽 미터(a_top=a)
        circ = math.pi * D
        # 미터 절단선은 원호가 아니라 사인곡선(반경 없음) → 공식/좌표법으로 명시
        sine = {"kind": "formula", "name": "미터 절단선",
                "expr": "절단선 = 중심 ± (조각길이/2 + a·cos(2π·x/원주))",
                "params": {"진폭 a": a, "원주": circ}}
        end_outline, end_fold = _gore_outline(r, end_half, 0.0, a,
                                              seam=seam, end_bottom=end)
        pat.add_panel(Panel("끝조각 End gore", end_outline, qty=2,
                            mark_lines=[end_fold] if end_fold else [],
                            curves=[sine],
                            texts=[(circ / 2, 0, "END x2")]))

        if n > 2:
            mid_outline, mid_fold = _gore_outline(r, mid_half, a, a, seam=seam)
            pat.add_panel(Panel("중간조각 Mid gore", mid_outline, qty=n - 2,
                                mark_lines=[mid_fold] if mid_fold else [],
                                curves=[sine],
                                texts=[(circ / 2, 0, f"MID x{n-2}")]))

        pat.add_row(항목="원주 πD", 값=round(math.pi * D, 1), 단위="mm")
        pat.add_row(항목="전개 폭(원주+심)", 값=round(math.pi * D + seam, 1), 단위="mm")
        pat.add_row(항목="조인트당 꺾임 β", 값=round(math.degrees(beta), 2), 단위="deg")
        pat.add_row(항목="끝조각 길이(중심선)", 값=round(R * beta / 2, 1), 단위="mm")
        pat.add_row(항목="중간조각 길이(중심선)", 값=round(R * beta, 1), 단위="mm")
        pat.add_row(항목="심 여유", 값=round(seam, 1), 단위="mm")
        pat.add_row(항목="단부 여유(끝조각)", 값=round(end, 1), 단위="mm")
        pat.add_row(항목="끝조각 수", 값=2, 단위="EA")
        pat.add_row(항목="중간조각 수", 값=max(n - 2, 0), 단위="EA")
        if warn <= 0:
            pat.notes.append("⚠ 목(throat)길이 음수: R을 키우거나 분할수 n을 늘리세요.")
        pat.notes.append(f"θ={p['angle']:g}°, n={n} / 심:{cfg.seam} / "
                         f"단부:{cfg.joint} / {cfg.gauge}GA")
        return pat
