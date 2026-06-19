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


def apply_win_taskbar_icon(win) -> None:
    """Windows 작업표시줄/제목표시줄 아이콘을 Win32 로 직접 설정.

    Qt setWindowIcon 이 작업표시줄까지 반영되지 않는 경우 대비.
    창이 생성된 뒤(show 이후) 호출해야 winId 가 유효하다.
    """
    if sys.platform != "win32":
        return
    ico = os.path.join(icon_dir(), "app.ico")
    if not os.path.exists(ico):
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        IMAGE_ICON = 1
        LR_LOADFROMFILE, LR_DEFAULTSIZE = 0x0010, 0x0040
        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1
        hwnd = int(win.winId())
        h_big = user32.LoadImageW(None, ico, IMAGE_ICON, 0, 0,
                                  LR_LOADFROMFILE | LR_DEFAULTSIZE)
        h_small = user32.LoadImageW(None, ico, IMAGE_ICON, 16, 16,
                                    LR_LOADFROMFILE)
        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
        if h_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_small)
    except Exception:  # noqa: BLE001 - 실패해도 앱 실행에는 지장 없음
        pass
