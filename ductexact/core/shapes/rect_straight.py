"""사각 직관 전개."""
from __future__ import annotations

from .. import allowances as al
from ..pattern import Pattern, Panel
from .base import Shape, ParamSpec, CommonSettings


class RectStraight(Shape):
    key = "rect_straight"
    name = "사각 직관"
    description = "직선 사각 덕트. 단일 블랭크(1심) 전개."

    params = [
        ParamSpec("W", "가로 W", "length", 300, "mm"),
        ParamSpec("H", "세로 H", "length", 250, "mm"),
        ParamSpec("L", "길이 L", "length", 1000, "mm"),
    ]

    def develop(self, p: dict[str, float], cfg: CommonSettings) -> Pattern:
        W = cfg.to_neutral(p["W"])
        H = cfg.to_neutral(p["H"])
        L = p["L"]
        seam = al.seam_allowance(cfg.seam, cfg.seam_table)
        end = al.end_allowance(cfg.joint, cfg.end_table)

        dev_w = 2 * (W + H) + seam
        dev_l = L + 2 * end

        # 외형: 좌하단 원점
        outline = [(0, 0), (dev_w, 0), (dev_w, dev_l), (0, dev_l)]

        # 접기선: 누적 W,H,W 위치 (네 면 분할 — 실제 절곡)
        folds = []
        for x in (W, W + H, 2 * W + H):
            folds.append(((x, 0), (x, dev_l)))

        # 여유 경계선(심·단부) — 접는 선이 아니라 본체/여유 경계 표시
        marks = []
        if seam > 0:
            marks.append(((2 * (W + H), 0), (2 * (W + H), dev_l)))
        if end > 0:
            marks.append(((0, end), (dev_w, end)))
            marks.append(((0, dev_l - end), (dev_w, dev_l - end)))

        texts = [(dev_w / 2, dev_l / 2, f"{self.name}  {W:g}x{H:g}, L={L:g}")]

        pat = Pattern(self.name)
        pat.add_panel(Panel("본체(Body)", outline, qty=1,
                            fold_lines=folds, mark_lines=marks, texts=texts))
        pat.add_row(항목="전개 폭", 값=round(dev_w, 1), 단위="mm")
        pat.add_row(항목="전개 길이", 값=round(dev_l, 1), 단위="mm")
        pat.add_row(항목="심 여유", 값=round(seam, 1), 단위="mm")
        pat.add_row(항목="단부 여유(편측)", 값=round(end, 1), 단위="mm")
        pat.add_row(항목="판재 면적", 값=round(dev_w * dev_l / 1e6, 4), 단위="m^2")
        pat.notes.append(f"심: {cfg.seam} / 단부: {cfg.joint} / {cfg.gauge}GA / 기준:{cfg.dim_basis}")
        return pat
