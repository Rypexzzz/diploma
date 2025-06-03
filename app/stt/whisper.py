"""Обёртка на чистом Python через библиотеку openai‑whisper (без бинарника whisper.cpp)."""
import asyncio, tempfile, wave
from pathlib import Path

import whisper  # pip install openai-whisper
from ..config import settings

# Загружаем модель один раз при импорте модуля
_model = whisper.load_model(settings.whisper_model_size)

TMP_DIR = Path(tempfile.gettempdir()) / "omo-cache"
TMP_DIR.mkdir(exist_ok=True)


def _transcribe_sync(pcm: bytes) -> str:
    """Блокирующая функция для запуска в ThreadPool."""
    wav_path = TMP_DIR / "chunk.wav"

    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(settings.sample_rate)
        wf.writeframes(pcm)

    result = _model.transcribe(str(wav_path), fp16=False)
    text = result["text"].strip()

    wav_path.unlink(missing_ok=True)
    return text


async def transcribe(pcm: bytes) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _transcribe_sync, pcm)