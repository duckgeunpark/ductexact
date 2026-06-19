"""matplotlib 기반 전개도 미리보기 캔버스."""
from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..core.pattern import Pattern

# 한글 라벨 깨짐 방지 (윈도우 기본 폰트)
matplotlib.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


class PreviewCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.fig = Figure(figsize=(5, 4), tight_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.clear()

    def clear(self):
        self.ax.clear()
        self.ax.set_aspect("equal", "box")
        self.ax.grid(True, ls=":", alpha=0.4)
        self.draw()

    def show_pattern(self, pattern: Pattern, gap: float = 50.0):
        self.ax.clear()
        self.ax.set_aspect("equal", "box")
        self.ax.grid(True, ls=":", alpha=0.4)

        cursor = 0.0
        for panel in pattern.panels:
            x0, y0, x1, y1 = panel.bbox()
            ox = cursor - x0
            oy = -y0
            xs = [p[0] + ox for p in panel.outline] + [panel.outline[0][0] + ox]
            ys = [p[1] + oy for p in panel.outline] + [panel.outline[0][1] + oy]
            self.ax.plot(xs, ys, "-", color="#1565c0", lw=1.5)
            for (a, b) in panel.fold_lines:
                self.ax.plot([a[0] + ox, b[0] + ox], [a[1] + oy, b[1] + oy],
                             "--", color="#2e7d32", lw=0.8)
            for (a, b) in panel.mark_lines:
                self.ax.plot([a[0] + ox, b[0] + ox], [a[1] + oy, b[1] + oy],
                             "-.", color="#ef6c00", lw=0.7)
            for (tx, ty, txt) in panel.texts:
                self.ax.text(tx + ox, ty + oy, txt, fontsize=7,
                             ha="center", va="center", color="#b00")
            cursor += (x1 - x0) + gap

        self.ax.set_title(pattern.shape_name, pad=18)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

    def show_drawing(self, drawing, gap: float = 120.0):
        from ..core.drawing import dim_geometry
        self.ax.clear()
        self.ax.set_aspect("equal", "box")
        self.ax.grid(True, ls=":", alpha=0.3)
        cursor = 0.0
        label_top = 0.0
        for view in drawing.views:
            x0, y0, x1, y1 = view.bbox()
            ox, oy = cursor - x0, -y0

            def T(p):
                return (p[0] + ox, p[1] + oy)

            for pl in view.polylines:
                xs = [p[0] + ox for p in pl]
                ys = [p[1] + oy for p in pl]
                self.ax.plot(xs, ys, "-", color="#1565c0", lw=1.4)
            import numpy as np
            for cx, cy, r in view.circles:
                t = np.linspace(0, 2 * np.pi, 80)
                self.ax.plot(cx + ox + r * np.cos(t), cy + oy + r * np.sin(t),
                             "-", color="#1565c0", lw=1.4)
            for (a, b) in view.fold_lines:
                self.ax.plot([a[0] + ox, b[0] + ox], [a[1] + oy, b[1] + oy],
                             "--", color="#2e7d32", lw=0.9)
            for d in view.dims:
                segs, tpos, txt, ang = dim_geometry(d)
                for a, b in segs:
                    self.ax.plot([a[0] + ox, b[0] + ox], [a[1] + oy, b[1] + oy],
                                 "-", color="#c62828", lw=0.7)
                self.ax.text(tpos[0] + ox, tpos[1] + oy, txt, fontsize=7,
                             color="#c62828", ha="center", va="center",
                             rotation=ang)
            for lb in view.labels:
                self.ax.text(lb.pos[0] + ox, lb.pos[1] + oy, lb.text,
                             fontsize=7, color="#333", ha="center")
            name_gap = max(12.0, (y1 - y0) * 0.04)
            label_top = max(label_top, (y1 - y0) + name_gap)
            self.ax.text(cursor, (y1 - y0) + name_gap, view.name, fontsize=8,
                         color="#000", va="bottom")
            cursor += (x1 - x0) + gap
        self.ax.set_title(drawing.shape_name, pad=18)
        self.ax.relim()
        self.ax.autoscale_view()
        # 뷰 제목이 잘리지 않도록 위쪽 여백 확보
        y_lo, y_hi = self.ax.get_ylim()
        self.ax.set_ylim(y_lo, max(y_hi, label_top + 12))
        self.draw()

    def show_nesting(self, result, gap: float = 200.0):
        self.ax.clear()
        self.ax.set_aspect("equal", "box")
        ox = 0.0
        for i, sheet in enumerate(result.sheets):
            sw, sh = sheet.width, sheet.height
            self.ax.plot([ox, ox + sw, ox + sw, ox, ox],
                         [0, 0, sh, sh, 0], "-", color="#888", lw=1.0)
            self.ax.text(ox, -sh * 0.04,
                         f"Sheet {i+1}  {sheet.utilization()*100:.0f}%",
                         fontsize=8, color="#333")
            for pl in sheet.placements:
                xs = [p[0] + ox for p in pl.outline] + [pl.outline[0][0] + ox]
                ys = [p[1] for p in pl.outline] + [pl.outline[0][1]]
                self.ax.fill(xs, ys, color="#90caf9", alpha=0.5)
                self.ax.plot(xs, ys, "-", color="#1565c0", lw=0.8)
            ox += sw + gap
        self.ax.set_title(f"네스팅 — {len(result.sheets)}장")
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()
