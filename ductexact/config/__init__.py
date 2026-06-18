"""설정 로더.

defaults.json 이 있으면 읽고(개발/현장 커스터마이즈), 없으면(예: 패키징된 exe)
allowances 모듈의 내장 기본값으로 폴백한다. 따라서 외부 파일이 없어도 절대
크래시하지 않는다.
"""
from __future__ import annotations

import json
import os
import sys

from ..core import allowances as al

_DIR = os.path.dirname(__file__)


def _builtin() -> dict:
    return {
        "seam_allowance_mm": dict(al.SEAM_ALLOWANCE_MM),
        "end_allowance_mm": dict(al.END_ALLOWANCE_MM),
        "gauge_thickness_mm": dict(al.GAUGE_THICKNESS_MM),
        "defaults": {
            "seam": "Pittsburgh",
            "joint": "Angle Flange + Bolt",
            "gauge": "18",
            "output_unit": "mm",
            "dim_basis": "ID",
        },
    }


def _candidate_paths() -> list[str]:
    paths = [os.path.join(_DIR, "defaults.json")]
    # PyInstaller 번들 경로
    base = getattr(sys, "_MEIPASS", None)
    if base:
        paths.append(os.path.join(base, "ductexact", "config", "defaults.json"))
    # exe 옆 폴더(사용자가 직접 둔 커스텀 설정)
    if getattr(sys, "frozen", False):
        paths.append(os.path.join(os.path.dirname(sys.executable),
                                  "defaults.json"))
    return paths


def load_config(path: str | None = None) -> dict:
    candidates = [path] if path else _candidate_paths()
    for p in candidates:
        if p and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 내장값과 병합(누락 키 보강)
                base = _builtin()
                base.update({k: v for k, v in data.items()
                             if not k.startswith("_")})
                return base
            except (OSError, json.JSONDecodeError):
                continue
    return _builtin()
