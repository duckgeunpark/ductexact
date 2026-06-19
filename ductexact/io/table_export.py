"""Pattern 치수표 -> CSV / 텍스트.

두 종류의 표를 제공한다.
- 요약표(`pattern.table`): 전개 폭/길이, 심·단부 여유 등 검산용 값.
- 도해표(`draw_table`): 좌표만으로 전개도를 따라 그릴 수 있는 작도표.
"""
from __future__ import annotations

import csv
import math

from ..core.pattern import Pattern
from ..core.units import from_mm


def table_rows(pattern: Pattern) -> list[dict]:
    return pattern.table


# ---------- 따라그리기(도해) 표 ----------
DRAW_HEADERS = ["패널", "구분", "번호", "X1", "Y1", "X2", "Y2", "길이/비고"]


def _simplify(pts: list, tol: float) -> list:
    """Douglas-Peucker 단순화. 직선부는 끝점만, 곡선부는 tol 내 필요한 점만 남김.

    표(따라그리기)용 점 개수를 줄이기 위함. 작도 허용오차 tol(mm).
    """
    if len(pts) < 3:
        return list(pts)

    def _dp(a: int, b: int) -> list[int]:
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        seg_len = math.hypot(dx, dy)
        dmax, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if seg_len == 0:
                d = math.hypot(px - ax, py - ay)
            else:                                   # 점-직선 수직거리
                d = abs(dy * px - dx * py + bx * ay - by * ax) / seg_len
            if d > dmax:
                dmax, idx = d, i
        if dmax > tol:
            return _dp(a, idx)[:-1] + _dp(idx, b)
        return [a, b]

    keep = _dp(0, len(pts) - 1)
    return [pts[i] for i in keep]


def _curve_rows(panel, c) -> list[list]:
    """패널의 곡선 정의(원호/공식)를 표 행으로. c: mm->출력단위 변환 함수."""
    rows: list[list] = []
    for cur in panel.curves:
        if cur.get("kind") == "arc":
            cx, cy, r = c(cur["cx"]), c(cur["cy"]), c(cur["r"])
            a0, a1 = cur["a0"], cur["a1"]
            rows.append(["", "곡선(원호)", cur.get("name", ""),
                         cx, cy, r, "",
                         f"중심({cx},{cy}) 반경 {r}, {a0:g}°→{a1:g}° (컴퍼스 작도)"])
        else:  # 공식 곡선(사인/교선 등) — 반경 없음, 좌표법
            parts = []
            for k, v in cur.get("params", {}).items():
                parts.append(f"{k}={c(v)}" if isinstance(v, (int, float))
                             else f"{k}={v}")
            params = " · ".join(parts)
            note = cur.get("expr", "")
            rows.append(["", "곡선(공식)", cur.get("name", ""),
                         "", "", "", "",
                         f"{note}{('  [' + params + ']') if params else ''}"])
    return rows


def draw_table(pattern: Pattern, out_unit: str = "mm",
               tol: float = 0.3) -> tuple[list[str], list[list]]:
    """좌표만으로 전개도를 작도할 수 있는 도해표. (헤더, 행들).

    각 패널을 좌하단을 (0,0) 으로 정규화한 좌표로 기술한다.
    - 곡선 정의: 원호는 중심·반경·각도, 사인/교선은 지배 공식(좌표법)으로 명시.
    - 외형: 점 P1..Pn 을 순서대로 직선으로 잇고 마지막은 P1 로 닫는다.
      직선부는 끝점만, 곡선부는 작도오차 tol(mm) 내 필요한 점만 남겨 솎는다.
      각 행의 (X1,Y1)=현재점, (X2,Y2)=다음점, 길이=그 변 길이.
    - 접기선 F* / 경계선 M*: (X1,Y1)-(X2,Y2) 직선과 길이.
    좌표·길이는 출력 단위로 변환해 소수 1자리 반올림.
    """
    def c(v: float) -> float:
        return round(from_mm(v, out_unit), 1)

    def seg(a, b):
        return math.hypot(b[0] - a[0], b[1] - a[1])

    rows: list[list] = []
    for panel in pattern.panels:
        x0, y0, x1, y1 = panel.bbox()

        def n(p):
            return (p[0] - x0, p[1] - y0)

        note = "전개폭 × 전개길이"
        if panel.curves:
            note += " · 곡선은 아래 곡선정의 참조"
        rows.append([panel.name, "패널", f"x{panel.qty}",
                     c(x1 - x0), c(y1 - y0), "", "", note])

        rows += _curve_rows(panel, c)

        pts = _simplify([n(p) for p in panel.outline], tol)
        m = len(pts)
        for i, p in enumerate(pts):
            q = pts[(i + 1) % m]                     # 마지막 점은 P1 로 닫힘
            rows.append(["", "외형", f"P{i + 1}",
                         c(p[0]), c(p[1]), c(q[0]), c(q[1]), c(seg(p, q))])
        for i, (a, b) in enumerate(panel.fold_lines, 1):
            a, b = n(a), n(b)
            rows.append(["", "접기선", f"F{i}",
                         c(a[0]), c(a[1]), c(b[0]), c(b[1]), c(seg(a, b))])
        for i, (a, b) in enumerate(panel.mark_lines, 1):
            a, b = n(a), n(b)
            rows.append(["", "경계선(심/단부)", f"M{i}",
                         c(a[0]), c(a[1]), c(b[0]), c(b[1]), c(seg(a, b))])
    return DRAW_HEADERS, rows


def export_draw_csv(pattern: Pattern, path: str, out_unit: str = "mm") -> str:
    """도해표를 CSV 로 저장. 단위 헤더 포함."""
    headers, rows = draw_table(pattern, out_unit)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"DuctExact 따라그리기 표 — {pattern.shape_name} (단위: {out_unit})"])
        w.writerow(headers)
        w.writerows(rows)
        if pattern.table:
            w.writerow([])
            w.writerow(["[검산용 요약]"])
            for r in pattern.table:
                w.writerow([f"{r.get('항목', '')}", r.get('값', ''), r.get('단위', '')])
    return path


def export_csv(pattern: Pattern, path: str) -> str:
    rows = pattern.table
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return path


def as_text(pattern: Pattern) -> str:
    lines = [f"[{pattern.shape_name}]"]
    for r in pattern.table:
        lines.append("  " + " | ".join(f"{k}: {v}" for k, v in r.items()))
    if pattern.notes:
        lines.append("-- 비고 --")
        lines.extend("  " + n for n in pattern.notes)
    return "\n".join(lines)
