"""공용 기하 유틸 (모든 단위 mm, 각도 라디안 내부 사용)."""
from __future__ import annotations

import math

Point = tuple[float, float]


def arc_points(cx: float, cy: float, r: float, a0: float, a1: float,
               n: int = 48) -> list[Point]:
    """중심(cx,cy), 반경 r 의 원호를 a0..a1(라디안) 구간 n+1 점으로."""
    pts: list[Point] = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def translate(points: list[Point], dx: float, dy: float) -> list[Point]:
    return [(x + dx, y + dy) for x, y in points]


def bbox(points: list[Point]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_area(points: list[Point]) -> float:
    """신발끈 공식. 닫힌 폴리곤 면적(절댓값)."""
    n = len(points)
    s = 0.0
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def dist(p0: Point, p1: Point) -> float:
    return math.hypot(p1[0] - p0[0], p1[1] - p0[1])


def circle_points_3d(cx: float, cy: float, cz: float, r: float,
                     n: int) -> list[tuple[float, float, float]]:
    """xy 평면 원을 3D 점으로 (삼각분할 전개용). 등분 n점(닫지 않음)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a), cz))
    return pts


def true_length(p0, p1) -> float:
    """3D 두 점 실거리 (삼각분할 전개용)."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p0, p1)))


def develop_strip(top: list, bottom: list,
                  closed: bool = False) -> tuple[list[Point], list[Point]]:
    """두 3D 점열(상/하단)을 삼각분할로 평면 전개. 반환: (top_2d, bottom_2d).

    각 i 의 top_2d[i]·bottom_2d[i] 가 대응(실길이 보존)하며, 둘을 이으면
    삼각분할(작도) 선이 된다.  외형은 top_2d + reversed(bottom_2d).
    """
    n = len(top)
    count = n if closed else n - 1

    # 하단 점들을 한 줄(기준선)에 누적 배치, 그에 매달아 상단 점 삼각측량
    bottom_2d: list[Point] = [(0.0, 0.0)]
    top_2d: list[Point] = []

    # 첫 상단점: 기준 하단점 위에 삼각형으로
    d_b0_t0 = true_length(bottom[0], top[0])
    top_2d.append((0.0, d_b0_t0))

    for i in range(count):
        j = (i + 1) % n
        bx, by = bottom_2d[i]
        tx, ty = top_2d[i]
        # 다음 하단점: 삼각형(B[i],T[i],B[i+1]). 공유변 (B[i],T[i]) 의
        # 직전 삼각형 꼭짓점은 T[i-1] → 그 반대쪽으로 펼쳐야 접히지 않음.
        l_bb = true_length(bottom[i], bottom[j])
        l_tb_next = true_length(top[i], bottom[j])
        ref_b = top_2d[i - 1] if i > 0 else None
        nb = _triangulate_point((bx, by), (tx, ty), l_bb, l_tb_next, ref_b)
        bottom_2d.append(nb)
        # 다음 상단점: 삼각형(T[i],B[i+1],T[i+1]). 공유변 (T[i],B[i+1]) 의
        # 직전 삼각형 꼭짓점은 B[i] → 그 반대쪽으로 펼친다.
        l_tt = true_length(top[i], top[j])
        l_tnb = true_length(top[j], bottom[j])
        nt = _triangulate_point((tx, ty), nb, l_tt, l_tnb, (bx, by))
        top_2d.append(nt)

    return top_2d, bottom_2d


def triangulate_strip(top: list, bottom: list, closed: bool = True) -> list[Point]:
    """두 3D 점열을 평면 전개한 닫힌 외형(상단 진행 후 하단 역순)."""
    top_2d, bottom_2d = develop_strip(top, bottom, closed)
    return top_2d + list(reversed(bottom_2d))


def segments_intersect(p1, p2, p3, p4) -> bool:
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = ccw(p3, p4, p1), ccw(p3, p4, p2)
    d3, d4 = ccw(p1, p2, p3), ccw(p1, p2, p4)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def polyline_self_intersects(poly: list[Point], tol: float = 1e-6) -> bool:
    """닫힌 폴리라인 자기교차 여부. 연속 중복점은 제거 후 판정."""
    pts: list[Point] = []
    for p in poly:
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > tol:
            pts.append(p)
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0],
                                   pts[0][1] - pts[-1][1]) <= tol:
        pts.pop()
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (i + 1) % n == j or (j + 1) % n == i:
                continue
            if segments_intersect(a, b, pts[j], pts[(j + 1) % n]):
                return True
    return False


def _triangulate_point(a: Point, b: Point, ra: float, rb: float,
                       ref: Point | None = None) -> Point:
    """a 에서 ra, b 에서 rb 떨어진 교점.

    ref 가 주어지면 직선 a→b 기준 ref 의 *반대쪽* 해를 고른다(스트립이
    공유변에서 접히지 않도록 일관된 방향으로 펼치기 위함). ref 가 없으면
    +90° 쪽을 고른다.
    """
    ax, ay = a
    bx, by = b
    # 공유 꼭짓점(0길이 변): 같은 점을 유지
    if ra == 0:
        return (ax, ay)
    if rb == 0:
        return (bx, by)
    d = math.hypot(bx - ax, by - ay)
    if d == 0:
        return (ax, ay + ra)
    # 원-원 교점 (두 해)
    aa = (ra * ra - rb * rb + d * d) / (2 * d)
    h = math.sqrt(max(ra * ra - aa * aa, 0.0))
    mx = ax + aa * (bx - ax) / d
    my = ay + aa * (by - ay) / d
    ux = -(by - ay) / d        # 직선 a→b 의 +90° 단위 법선
    uy = (bx - ax) / d
    p_plus = (mx + ux * h, my + uy * h)
    if ref is None:
        return p_plus

    def side(px, py):
        return (bx - ax) * (py - ay) - (by - ay) * (px - ax)

    if (side(*p_plus) > 0) == (side(ref[0], ref[1]) > 0):
        return (mx - ux * h, my - uy * h)   # ref 와 반대쪽 해
    return p_plus
