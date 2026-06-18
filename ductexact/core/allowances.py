"""제작 여유값: 심(seam)·단부 연결(joint)·게이지(두께). 모두 mm.

기본값은 SMACNA 통상값 기반의 합리적 추정치이며, config/defaults.json 으로
현장 표준에 맞게 덮어쓸 수 있다.  실제 절단 치수에 직접 영향을 주므로
공장 표준이 있으면 반드시 교체할 것.
"""
from __future__ import annotations

# 심 방식별 "전개 폭에 더해지는 총 여유(mm)" — 양쪽 맞물림 변 합산
SEAM_ALLOWANCE_MM: dict[str, float] = {
    "Pittsburgh": 22.0,
    "Snap Lock": 16.0,
    "Button Punch": 16.0,
    "Drive Cleat": 12.0,
    "None": 0.0,
}

# 단부 연결별 "한쪽 끝에 더해지는 여유(mm)" — 길이 방향, 양 끝에 각각 적용
END_ALLOWANCE_MM: dict[str, float] = {
    "Angle Flange + Bolt": 0.0,   # 앵글은 별물, 덕트 단부는 맞댐
    "TDC": 9.5,
    "TDF": 9.5,
    "S&D (Slip & Drive)": 6.0,
    "None": 0.0,
}

# 게이지(GA) -> 두께(mm). 아연도금강판(GS) 기준 통상값.
GAUGE_THICKNESS_MM: dict[str, float] = {
    "30": 0.40,
    "28": 0.48,
    "26": 0.55,
    "24": 0.70,
    "22": 0.85,
    "20": 1.00,
    "18": 1.31,
    "16": 1.61,
    "14": 1.99,
}

# 굽힘 여유(bend allowance) K-factor 기본값 (사용 시)
DEFAULT_K_FACTOR = 0.44


def seam_allowance(name: str, table: dict[str, float] | None = None) -> float:
    t = table or SEAM_ALLOWANCE_MM
    return float(t.get(name, 0.0))


def end_allowance(name: str, table: dict[str, float] | None = None) -> float:
    t = table or END_ALLOWANCE_MM
    return float(t.get(name, 0.0))


def gauge_thickness(name: str, table: dict[str, float] | None = None) -> float:
    t = table or GAUGE_THICKNESS_MM
    return float(t.get(str(name), 1.0))
