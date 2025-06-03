# app/__main__.py
from __future__ import annotations
import asyncio, signal, sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .gui.mainwindow import MainWindow


def _load_global_qss() -> str:
    """читаем файл gui/style_light.qss (лежит рядом с mainwindow.py)"""
    qss_path = Path(__file__).parent / "gui" / "style_light.qss"
    return qss_path.read_text(encoding="utf-8")


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")                       # базовый светлый стиль
    app.setStyleSheet(_load_global_qss())        # наш QSS — один раз для всего приложения

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            pass

    win = MainWindow()
    win.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
