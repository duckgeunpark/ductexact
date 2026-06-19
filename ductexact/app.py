"""DuctExact 진입점."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.resources import app_icon


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
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())   # 작업표시줄/전역 기본 아이콘
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
