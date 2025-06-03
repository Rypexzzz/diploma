"""Runtime‑загрузка .ui файлов (ленивая, после QApplication)"""
from pathlib import Path
from PySide6.QtCore import QFile


def load_ui(name: str):
    """Возвращает QWidget из .ui файла (лежит в том же каталоге)."""
    from PySide6.QtUiTools import QUiLoader  # импорт внутри функции → безопасно до QApplication
    ui_file = Path(__file__).parent / f"{name}.ui"
    f = QFile(str(ui_file))
    f.open(QFile.ReadOnly)
    try:
        loader = QUiLoader()
        return loader.load(f)
    finally:
        f.close()