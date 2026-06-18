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


def triangulate_strip(top: list, bottom: list, closed: bool = True) -> list[Point]:
    """두 3D 점열(상/하단 둘레)을 삼각분할로 평면 전개.

    인접한 top[i],bottom[i],top[i+1],bottom[i+1] 사각형을 두 삼각형으로
    나눠 실길이를 유지하며 평면에 펼친다.  닫힌 둘레면 마지막을 처음과 연결.
    반환: 전개된 외형 폴리라인(상단 진행 후 하단 역순)으로 닫힌 형상.
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
        # 다음 하단점: 현재 하단점 + 현재 상단점에서 삼각측량
        l_bb = true_length(bottom[i], bottom[j])
        l_tb_next = true_length(top[i], bottom[j])
        nb = _triangulate_point((bx, by), (tx, ty), l_bb, l_tb_next)
        bottom_2d.append(nb)
        # 다음 상단점: 다음 하단점 + 현재 상단점에서
        l_tt = true_length(top[i], top[j])
        l_tnb = true_length(top[j], bottom[j])
        nt = _triangulate_point((tx, ty), nb, l_tt, l_tnb)
        top_2d.append(nt)

    outline = top_2d + list(reversed(bottom_2d))
    return outline


def _triangulate_point(a: Point, b: Point, ra: float, rb: float) -> Point:
    """a 에서 ra, b 에서 rb 떨어진 교점(진행 방향 기준 한 쪽)."""
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
    # 원-원 교점
    aa = (ra * ra - rb * rb + d * d) / (2 * d)
    h2 = ra * ra - aa * aa
    h = math.sqrt(max(h2, 0.0))
    mx = ax + aa * (bx - ax) / d
    my = ay + aa * (by - ay) / d
    # 진행 방향(전개가 +x 로 퍼지도록) 한쪽 선택
    ox = -(by - ay) / d * h
    oy = (bx - ax) / d * h
    return (mx + ox, my + oy)
