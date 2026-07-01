"""형상별 정투상 완성도(조립도) 생성.

입력 p 는 사용자가 입력한 '설계 치수'(mm) 그대로 사용 — 완성된 부재의
공칭 치수를 도면에 표기한다(전개의 중립선 보정과는 별개).
"""
from __future__ import annotations

import math

from . import geometry as g
from .drawing import AssemblyDrawing, View, LinearDim, Label

DG = 60.0   # 치수선 기본 오프셋(mm)


def _rect(x: float, y: float, w: float, h: float) -> list[tuple[float, float]]:
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def build_drawing(key: str, p: dict, cfg=None) -> AssemblyDrawing:
    fn = _BUILDERS.get(key)
    if fn is None:
        return AssemblyDrawing("(완성도 미지원)", [], ["이 형상은 완성도 미지원."])
    return fn(p)


# ---------------- 직관 ----------------
def _rect_straight(p):
    W, H, L = p["W"], p["H"], p["L"]
    end = View("정면도(단면)", [_rect(0, 0, W, H)])
    end.dims = [
        LinearDim((0, 0), (W, 0), (0, -DG), 0, f"W {W:g}"),
        LinearDim((0, 0), (0, H), (-DG, 0), 90, f"H {H:g}"),
    ]
    side = View("측면도", [_rect(0, 0, L, H)])
    side.dims = [
        LinearDim((0, 0), (L, 0), (0, -DG), 0, f"L {L:g}"),
        LinearDim((0, 0), (0, H), (-DG, 0), 90, f"H {H:g}"),
    ]
    return AssemblyDrawing("사각 직관 완성도", [end, side])


def _round_straight(p):
    D, L = p["D"], p["L"]
    end = View("정면도", circles=[(D / 2, D / 2, D / 2)])
    end.dims = [LinearDim((0, D / 2), (D, D / 2), (0, -DG), 0, f"Ø{D:g}")]
    side = View("측면도", [_rect(0, 0, L, D)])
    side.dims = [
        LinearDim((0, 0), (L, 0), (0, -DG), 0, f"L {L:g}"),
        LinearDim((0, 0), (0, D), (-DG, 0), 90, f"Ø{D:g}"),
    ]
    return AssemblyDrawing("원형 직관 완성도", [end, side])


# ---------------- 엘보 ----------------
def _rect_elbow(p):
    """완성도(조립도): 조립된 엘보 측면도 + 입구 단면도. (절단상세는 전개도 탭)"""
    from .shapes.rect_elbow import cheek_outline
    W, H, Rt = p["W"], p["H"], p["Rt"]
    ang = p["angle"]
    th = math.radians(ang)
    leg1 = p.get("leg1", 50.0)      # 입구단 직관
    leg2 = p.get("leg2", 50.0)      # 출구단 직관
    Rh = Rt + W
    mid = th / 2
    cm, sm = math.cos(mid), math.sin(mid)

    # --- 측면도: 조립된 엘보 실루엣(호 + 양단 직관) ---
    profile = cheek_outline(Rt, Rh, th, leg1, leg2, 60)
    side = View(f"{ang:g}° 엘보 측면도", [profile])
    side.labels = [
        Label((Rt * cm * 0.85, Rt * sm * 0.85), f"R{Rt:g}"),
        Label((Rh * cm * 0.95, Rh * sm * 0.95), f"R{Rh:g}"),
        Label((Rt * cm * 0.32, Rt * sm * 0.32), f"{ang:g}°"),
    ]
    side.dims = [
        LinearDim((Rt, -leg1), (Rh, -leg1), (0, -leg1 - DG), 0, f"W {W:g}"),
        LinearDim((Rh, -leg1), (Rh, 0), (Rh + DG, 0), 90, f"입구직관 {leg1:g}"),
    ]

    # --- 단면도: 입구 W×H ---
    sec = View("단면도 A-A", [_rect(0, 0, W, H)])
    sec.dims = [
        LinearDim((0, 0), (W, 0), (0, -DG), 0, f"W {W:g}"),
        LinearDim((0, 0), (0, H), (-DG, 0), 90, f"H {H:g}"),
    ]
    return AssemblyDrawing(f"{ang:g}° 사각 엘보 완성도", [side, sec])


def _round_elbow(p):
    D, R = p["D"], p["R"]
    th = math.radians(p["angle"])
    n = int(p["n"])
    ro, ri = R + D / 2, R - D / 2
    outer = g.arc_points(0, 0, ro, 0, th, 60)
    inner = g.arc_points(0, 0, ri, th, 0, 60)
    profile = outer + inner + [outer[0]]
    prof = View("측면도(새우관)", [profile])
    # 분할(미터) 선: 끝 1/2 + 중간 온조각
    beta = th / (n - 1)
    cuts = [beta / 2 + beta * i for i in range(n - 1)]
    for a in cuts:
        prof.polylines.append([(ri * math.cos(a), ri * math.sin(a)),
                               (ro * math.cos(a), ro * math.sin(a))])
    prof.labels = [
        Label((R * math.cos(th / 2), R * math.sin(th / 2)), f"R{R:g}"),
        Label((ro * math.cos(th / 2) * 1.03, ro * math.sin(th / 2) * 1.03),
              f"Ø{D:g}  {p['angle']:g}°  n={n}"),
    ]
    return AssemblyDrawing("원형 엘보 완성도", [prof])


# ---------------- 리듀서 ----------------
def _reducer(p):
    kind = p.get("kind", "원형→원형")
    L = p["L"]
    a1 = p["D1"]            # 입구 폭/지름
    a2 = p["D2"]            # 출구 폭/지름
    # 측면도: 동심 사다리꼴
    y1, y2 = a1 / 2, a2 / 2
    side_poly = [(0, -y1), (0, y1), (L, y2), (L, -y2), (0, -y1)]
    side = View("측면도", [side_poly])
    side.dims = [
        LinearDim((0, -y1), (0, y1), (-DG, 0), 90, f"{a1:g}"),
        LinearDim((L, -y2), (L, y2), (L + DG, 0), 90, f"{a2:g}"),
        LinearDim((0, -y1), (L, -y1), (0, -y1 - DG), 0, f"L {L:g}"),
    ]
    views = [side]
    # 정면도: 입·출구 단면 겹쳐서
    front = View("정면도(입/출구)")
    if "원형" in kind.split("→")[0]:
        front.circles.append((0, 0, a1 / 2))
    else:
        front.polylines.append(_rect(-a1 / 2, -p["H1"] / 2, a1, p["H1"]))
    if "원형" in kind.split("→")[1]:
        front.circles.append((0, 0, a2 / 2))
    else:
        front.polylines.append(_rect(-a2 / 2, -p["H2"] / 2, a2, p["H2"]))
    front.labels = [Label((0, a1 / 2 + 20), kind)]
    views.append(front)
    return AssemblyDrawing("리듀서 완성도", views)


# ---------------- 티/와이 ----------------
def _round_tee(p):
    Dm, Db, Lb = p["Dm"], p["Db"], p["Lb"]
    a = math.radians(p["angle"])
    Lmain = max(Dm * 3, Db * 2)
    cx = Lmain / 2
    top = Dm / 2                          # 본관 윗면(분기가 붙는 표면)
    dx, dy = math.cos(a), math.sin(a)     # 분기축 방향
    sin_a = max(math.sin(a), 1e-6)
    half = Db / (2 * sin_a)               # 본관 표면에서의 분기 개구 반폭
    bl = (cx - half, top)                 # 개구(분기 벽이 표면과 만나는 점) 좌
    br = (cx + half, top)                 # 개구 우
    tl = (bl[0] + Lb * dx, bl[1] + Lb * dy)   # 분기 끝 좌
    tr = (br[0] + Lb * dx, br[1] + Lb * dy)   # 분기 끝 우
    # 본관: 윗변에 분기 개구만큼 끊어서(개구) 그린다
    main_lower = [(0, -Dm / 2), (Lmain, -Dm / 2), (Lmain, top), br]
    main_upper = [bl, (0, top), (0, -Dm / 2)]
    # 분기: 본관 표면 위로 올라앉는(각도 a) 평행사변형, 밑변은 개구라 열어둔다
    branch = [bl, tl, tr, br]
    v = View("측면도", [main_lower, main_upper, branch])
    v.dims = [
        LinearDim((0, -Dm / 2), (Lmain, -Dm / 2), (0, -Dm / 2 - DG), 0, f"본관 Ø{Dm:g}"),
    ]
    v.labels = [
        Label(((tl[0] + tr[0]) / 2, (tl[1] + tr[1]) / 2 + 15), f"Ø{Db:g} L{Lb:g}"),
        Label((br[0] + 15, top + 20), f"{p['angle']:g}°"),
    ]
    return AssemblyDrawing("원형 티/와이 완성도", [v])


def _rect_tee(p):
    Wm, Hm, Wb, Hb, Lb = p["Wm"], p["Hm"], p["Wb"], p["Hb"], p["Lb"]
    Lmain = max(Wm * 3, Wb * 2)
    cx = Lmain / 2
    bl = (cx - Wb / 2, Hm)               # 분기 개구 좌
    br = (cx + Wb / 2, Hm)               # 분기 개구 우
    # 본관: 윗변에 분기 개구만큼 끊어서 그린다
    main_lower = [(0, 0), (Lmain, 0), (Lmain, Hm), br]
    main_upper = [bl, (0, Hm), (0, 0)]
    # 분기: 밑변(개구)은 열어두고 ㄷ자로
    branch = [bl, (cx - Wb / 2, Hm + Lb), (cx + Wb / 2, Hm + Lb), br]
    v = View("측면도", [main_lower, main_upper, branch])
    v.dims = [
        LinearDim((0, 0), (Lmain, 0), (0, -DG), 0, f"본관 {Wm:g}x{Hm:g}"),
        LinearDim((cx - Wb / 2, Hm), (cx - Wb / 2, Hm + Lb), (cx - Wb / 2 - DG, 0), 90, f"L {Lb:g}"),
        LinearDim((cx - Wb / 2, Hm + Lb), (cx + Wb / 2, Hm + Lb), (0, Hm + Lb + DG), 0, f"분기 {Wb:g}"),
    ]
    return AssemblyDrawing("사각 티 완성도", [v])


_BUILDERS = {
    "rect_straight": _rect_straight,
    "round_straight": _round_straight,
    "rect_elbow": _rect_elbow,
    "round_elbow": _round_elbow,
    "reducer": _reducer,
    "round_tee": _round_tee,
    "rect_tee": _rect_tee,
}
