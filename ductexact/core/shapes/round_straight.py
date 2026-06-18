"""원형 직관 전개 (원주를 펼친 직사각형)."""
from __future__ import annotations

import math

from .. import allowances as al
from ..pattern import Pattern, Panel
from .base import Shape, ParamSpec, CommonSettings


class RoundStraight(Shape):
    key = "round_straight"
    name = "원형 직관"
    description = "직선 원형 덕트. 원주 전개 = π·D × 길이."

    params = [
        ParamSpec("D", "지름 D", "length", 300, "mm"),
        ParamSpec("L", "길이 L", "length", 1000, "mm"),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        D = cfg.to_neutral(p["D"])
        L = p["L"]
        seam = al.seam_allowance(cfg.seam, cfg.seam_table)
        end = al.end_allowance(cfg.joint, cfg.end_table)

        circ = math.pi * D
        dev_w = circ + seam
        dev_l = L + 2 * end

        outline = [(0, 0), (dev_w, 0), (dev_w, dev_l), (0, dev_l)]
        folds = []
        if seam > 0:
            folds.append(((circ, 0), (circ, dev_l)))
        if end > 0:
            folds.append(((0, end), (dev_w, end)))
            folds.append(((0, dev_l - end), (dev_w, dev_l - end)))

        texts = [(dev_w / 2, dev_l / 2, f"{self.name}  Ø{D:g}, L={L:g}")]

        pat = Pattern(self.name)
        pat.add_panel(Panel("본체(Body)", outline, qty=1,
                            fold_lines=folds, texts=texts))
        pat.add_row(항목="원주 πD", 값=round(circ, 1), 단위="mm")
        pat.add_row(항목="전개 폭", 값=round(dev_w, 1), 단위="mm")
        pat.add_row(항목="전개 길이", 값=round(dev_l, 1), 단위="mm")
        pat.add_row(항목="판재 면적", 값=round(dev_w * dev_l / 1e6, 4), 단위="m^2")
        pat.notes.append(f"심: {cfg.seam} / 단부: {cfg.joint} / {cfg.gauge}GA")
        return pat
