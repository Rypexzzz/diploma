# app/__main__.py
from __future__ import annotations
import asyncio, signal, sys
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .gui.mainwindow import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")                       # базовый светлый стиль
    # тема применяется в MainWindow

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
