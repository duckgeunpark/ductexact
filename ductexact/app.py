"""DuctExact 진입점."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.resources import app_icon, apply_win_taskbar_icon


def _set_windows_app_id() -> None:
    """작업표시줄이 파이썬이 아닌 DuctExact 아이콘으로 묶이도록 AppUserModelID 지정."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "DuctExact.App")
    except Exception:  # noqa: BLE001 - 실패해도 앱 실행에는 지장 없음
        pass


def main() -> int:
    # 작업표시줄이 창 아이콘을 쓰도록 AppID 지정.
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())   # 창 제목표시줄/전역 기본 아이콘
    win = MainWindow()
    win.show()
    # show 이후 winId 가 유효 → Win32 로 작업표시줄 아이콘 직접 강제 적용
    apply_win_taskbar_icon(win)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
