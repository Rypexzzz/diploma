from __future__ import annotations
import asyncio, datetime, json, re, subprocess
from pathlib import Path

import keyboard
import qtawesome as qta
from qasync import asyncSlot
from PySide6.QtCore    import Qt, QSize, QTimer, QPropertyAnimation
from PySide6.QtGui     import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QRadioButton, QSlider, QSplitter, QStatusBar, QToolBar,
    QVBoxLayout, QWidget, QSizePolicy, QButtonGroup, QGraphicsOpacityEffect
)

from ..workflows import recorder, summarizer

# ────────── QSS-файлы ──────────────────────────────────────────
_QSS_DIR = Path(__file__).parent
THEMES = {
    "light": _QSS_DIR / "style_light.qss",
    "dark":  _QSS_DIR / "style_dark.qss",
}

# ────────── helpers ───────────────────────────────────────────
def list_ollama_models() -> list[str]:
    try:
        raw = subprocess.check_output(["ollama", "list", "--json"],
                                      text=True, timeout=5, stderr=subprocess.DEVNULL)
        return [m["name"] for m in json.loads(raw)]
    except Exception:
        try:
            raw = subprocess.check_output(["ollama", "list"],
                                          text=True, timeout=5, stderr=subprocess.DEVNULL)
            return [l.split()[0] for l in raw.strip().splitlines()[1:]] or ["deepseek-r1:32b"]
        except Exception:
            return ["deepseek-r1:32b"]


def categorize(models: list[str]) -> dict[str, str]:
    low  = next((m for m in models if re.search(r"phi|tiny", m)), None) or models[0]
    mid  = next((m for m in models if re.search(r"8b|13b|mistral", m)), None) or models[min(1, len(models)-1)]
    high = next((m for m in models if re.search(r"32b|70b|deepseek|34b", m)), None) or models[-1]
    return {"low": low, "mid": mid, "high": high}

# ────────── диалог настроек ───────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, parent: QMainWindow,
                 model_map: dict[str, str], cur_key: str, cur_style: str, cur_theme: str):
        super().__init__(parent)
        self.setWindowTitle("Параметры"); self.resize(430, 320)
        self.model_map = model_map

        self.sld = QSlider(Qt.Horizontal); self.sld.setRange(0,2); self.sld.setTickInterval(1)
        self.sld.setTickPosition(QSlider.TicksBelow)
        self.sld.setValue({"low":0,"mid":1,"high":2}[cur_key])
        self.lblModel = QLabel(); self._upd_model(); self.sld.valueChanged.connect(self._upd_model)

        self.rbBullet   = QRadioButton("Маркированный список\n• кратко о решениях")
        self.rbLetter   = QRadioButton("Письмо-резюме\nкороткий абзац для почты")
        self.rbProtocol = QRadioButton("Подробный протокол\nвопрос, решение, ответственный")

        self.rbLight = QRadioButton("Светлая тема")
        self.rbDark  = QRadioButton("Тёмная тема")

        {"bullet": self.rbBullet, "letter": self.rbLetter, "protocol": self.rbProtocol}[cur_style].setChecked(True)
        {"light": self.rbLight, "dark": self.rbDark}[cur_theme].setChecked(True)

        # отдельные группы радиокнопок
        self.grpStyle = QButtonGroup(self)
        self.grpStyle.addButton(self.rbBullet)
        self.grpStyle.addButton(self.rbLetter)
        self.grpStyle.addButton(self.rbProtocol)

        self.grpTheme = QButtonGroup(self)
        self.grpTheme.addButton(self.rbLight)
        self.grpTheme.addButton(self.rbDark)

        form = QFormLayout()
        form.addRow("Модель суммирования:", self.sld)
        form.addRow("", self.lblModel)
        form.addRow("Формат резюме:", self.rbBullet)
        form.addRow("", self.rbLetter); form.addRow("", self.rbProtocol)
        form.addRow("Тема оформления:", self.rbLight)
        form.addRow("", self.rbDark)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)

        hint = QLabel("Добавить модели: <code>ollama pull &lt;имя&gt;</code>")
        hint.setTextFormat(Qt.RichText)

        lay = QVBoxLayout(self); lay.addLayout(form); lay.addWidget(hint); lay.addWidget(buttons)

    @property
    def model_key(self) -> str: return {0:"low",1:"mid",2:"high"}[self.sld.value()]
    @property
    def style(self) -> str: return "bullet" if self.rbBullet.isChecked() else \
                               "letter" if self.rbLetter.isChecked() else "protocol"
    @property
    def theme(self) -> str:
        return "dark" if self.rbDark.isChecked() else "light"

    def _upd_model(self):
        k = self.model_key
        name = {"low":"Лёгкая","mid":"Средняя","high":"Максимальная"}[k]
        self.lblModel.setText(f"<b>{name}</b><br><small>{self.model_map[k]}</small>")


# ────────── главное окно ───────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Оптимизатор онлайн-встреч"); self.resize(1360, 820)

        self._model_map = categorize(list_ollama_models())
        self.model_key = "mid"; self.summary_style = "bullet"; self.theme = "dark"

        self._pcm_chunks: list[bytes] = []
        self._timer_live = QTimer(interval=2000); self._timer_live.timeout.connect(self._flush_live)

        self._build_ui(); self._apply_theme(); self._hotkey_global()

    # UI ---------------------------------------------------------------
    def _build_ui(self):
        self.lblTitle = QLabel("Инструмент для работы с онлайн-встречами",
                               alignment=Qt.AlignCenter, objectName="Title")

        tb = QToolBar(self); tb.setMovable(False); tb.setIconSize(QSize(36,36))
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon); self.addToolBar(tb)

        self.actRecord = QAction(qta.icon("fa5s.microphone-alt"), "Запись", self)
        self.actOpen   = QAction(qta.icon("fa5s.folder-open"),    "Открыть", self)
        self.actSave   = QAction(qta.icon("fa5s.save"),           "Сохранить", self)
        self.actSett   = QAction(qta.icon("fa5s.cog"),            "Параметры", self)
        tb.addActions([self.actRecord, self.actOpen, self.actSave]); self.actSave.setEnabled(False)
        tb.addSeparator(); tb.addAction(self.actSett)

        splitter = QSplitter(Qt.Horizontal, self)
        self.txtTr = QPlainTextEdit(readOnly=True); self.txtSm = QPlainTextEdit(readOnly=True)
        splitter.addWidget(self._col("Транскрипция", self.txtTr))
        splitter.addWidget(self._col("Резюме",        self.txtSm))
        splitter.setSizes([680,680])

        self.lblStage = QLabel("Готово", alignment=Qt.AlignCenter, objectName="StageLabel")
        self.pbar = QProgressBar(); self.pbar.setRange(0,0); self.pbar.setVisible(False)
        self.lblCfg = QLabel(self._cfg_txt())

        sb = QStatusBar(self)
        sp = QWidget(); sp.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        sb.addPermanentWidget(self.lblCfg); sb.addPermanentWidget(sp)
        sb.addPermanentWidget(self.pbar); sb.addPermanentWidget(QWidget(),1)
        self.setStatusBar(sb)

        lay = QVBoxLayout(); root = QWidget(); root.setLayout(lay)
        lay.addWidget(self.lblTitle); lay.addWidget(self.lblStage)
        lay.addWidget(splitter); lay.setStretch(2,1)
        self.setCentralWidget(root)

        self.actRecord.triggered.connect(self._rec_toggle)
        self.actOpen.triggered.connect(self._open_audio)
        self.actSave.triggered.connect(self._save_md)
        self.actSett.triggered.connect(self._show_settings)

    def _col(self,title:str,w:QPlainTextEdit)->QWidget:
        lbl=QLabel(title,objectName="Header")
        col=QWidget();lay=QVBoxLayout(col);lay.addWidget(lbl);lay.addWidget(w);lay.setStretch(1,1);return col

    def _cfg_txt(self)->str:
        m={"low":"Лёгкая","mid":"Средняя","high":"Максимальная"}[self.model_key]
        s={"bullet":"список","letter":"письмо","protocol":"протокол"}[self.summary_style]
        t={"light":"светлая","dark":"тёмная"}[self.theme]
        return f"Модель: {m} | Формат: {s} | Тема: {t}"

    def _apply_theme(self):
        # лёгкая анимация плавного переключения темы
        root = self.centralWidget()
        effect = QGraphicsOpacityEffect(root)
        root.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.finished.connect(lambda: root.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

        qss = THEMES[self.theme]
        QApplication.instance().setStyleSheet(qss.read_text(encoding="utf-8"))

    def _hotkey_global(self):
        keyboard.add_hotkey("ctrl+alt+shift+r",
            lambda: QApplication.postEvent(self,
              QKeySequence("Ctrl+R").toKeyCombination().toEventType()))
        self.actRecord.setShortcut(QKeySequence("Ctrl+R"))

    # настройки
    def _show_settings(self):
        d=SettingsDialog(self,self._model_map,self.model_key,self.summary_style,self.theme)
        if d.exec():
            self.model_key,self.summary_style,self.theme=d.model_key,d.style,d.theme
            self.lblCfg.setText(self._cfg_txt()); self._apply_theme()

    # запись
    @asyncSlot()
    async def _rec_toggle(self):
        if getattr(self,"_task",None) is None:
            self._reset(); self.stop_evt=asyncio.Event(); self._pcm_chunks.clear()
            self._stage("Запись…",True); self.actRecord.setIcon(qta.icon("fa5s.square")); self.actRecord.setText("Стоп")
            self._timer_live.start(); self._task=asyncio.create_task(self._loop_record())
        else:
            self.stop_evt.set(); self.actRecord.setEnabled(False); self._timer_live.stop()

    async def _loop_record(self):
        try:
            async for chunk in recorder.stream_async():
                self._pcm_chunks.append(chunk)
                if self.stop_evt.is_set(): break
            await self._process_pcm(b"".join(self._pcm_chunks))
        except Exception as e: QMessageBox.critical(self,"Ошибка",str(e))
        finally:
            self._stage("Готово",False); self.actRecord.setIcon(qta.icon("fa5s.microphone-alt")); self.actRecord.setText("Запись")
            self.actRecord.setEnabled(True); self._task=None

    def _flush_live(self):
        if self._pcm_chunks: asyncio.create_task(self._upd_live(b"".join(self._pcm_chunks)))
    async def _upd_live(self,pcm:bytes): self.txtTr.setPlainText(await summarizer.stt_chunk(pcm))

    # файл
    @asyncSlot()
    async def _open_audio(self):
        p,_ = QFileDialog.getOpenFileName(self,"Выберите аудио","","Audio (*.wav *.mp3 *.flac *.m4a)")
        if not p: return
        self._reset(); self._stage("Расшифровка…",True)
        try: await self._process_pcm(recorder.bytes_from_file(p), Path(p), save_wav=False)
        except Exception as e: QMessageBox.critical(self,"Ошибка",str(e))
        finally: self._stage("Готово",False)

    def _save_md(self):
        if not getattr(self,"_last_md",None): return
        tgt,_=QFileDialog.getSaveFileName(self,"Сохранить",str(self._last_md),"Markdown (*.md)")
        if tgt: Path(self._last_md).rename(tgt); QMessageBox.information(self,"Сохранено","Файл сохранён")

    # обработка
    async def _process_pcm(self,pcm:bytes,src:Path|None=None,*,save_wav=True):
        self.txtTr.setPlainText(await summarizer.stt(pcm))
        self._stage("Суммирование…",True)
        sm=await summarizer.summarize(self.txtTr.toPlainText(),
            model=self._model_map[self.model_key],style=self.summary_style)
        self.txtSm.setPlainText(sm); self._stage("Готово",False)
        if save_wav and src is None:
            stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            src=Path(f"meeting_{stamp}.wav").resolve(); recorder.write_wav(src,pcm)
        if src:
            md=src.with_suffix(".md"); md.write_text(sm,encoding="utf-8")
            self._last_md=md; self.actSave.setEnabled(True)

    # утилиты
    def _stage(self,t,busy): self.lblStage.setText(t); self.pbar.setVisible(busy)
    def _reset(self): self.txtTr.clear(); self.txtSm.clear(); self.actSave.setEnabled(False)
