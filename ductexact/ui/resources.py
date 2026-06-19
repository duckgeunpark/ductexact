"""아이콘 등 리소스 경로 해석. 개발 실행/PyInstaller 번들 양쪽 지원."""
from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon


def _base_dir() -> str:
    """리소스 루트. 번들(frozen)이면 _MEIPASS, 아니면 프로젝트 루트."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    # ductexact/ui/resources.py -> 프로젝트 루트
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def icon_dir() -> str:
    return os.path.join(_base_dir(), "icon")


def app_icon() -> QIcon:
    """앱/창 아이콘. 여러 해상도를 한 QIcon 에 담아 OS 가 알맞은 크기를 고르게 한다."""
    d = icon_dir()
    icon = QIcon()
    # 우선순위: 멀티해상도 .ico → 개별 png(16/48/72)
    ico = os.path.join(d, "app.ico")
    if os.path.exists(ico):
        icon.addFile(ico)
    for name in ("icon-16x16.png", "icon-48x48.png", "icon-72x72.png"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            icon.addFile(p)
    return icon
