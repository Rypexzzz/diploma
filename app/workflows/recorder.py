from __future__ import annotations
import asyncio, io, wave
from pathlib import Path
from typing import AsyncGenerator

from pydub import AudioSegment
from ..audio import capture


async def stream_async() -> AsyncGenerator[bytes, None]:
    async for chunk in capture.stream_async():
        yield chunk


def bytes_from_file(path: str) -> bytes:
    audio = AudioSegment.from_file(path)
    audio = audio.set_channels(1).set_frame_rate(48_000).set_sample_width(2)
    buf = io.BytesIO(); audio.export(buf, format="raw")
    return buf.getvalue()


def write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(48_000)
        wf.writeframes(pcm)


async def stream_async():
    """Генератор PCM-фреймов по 2 × 48000 × 1 байт ≈ 1 с"""
    buf = bytearray()
    async for chunk in capture.stream_async():
        buf.extend(chunk)
        if len(buf) >= 96_000:          # 1 с при 48 кГц, 16-бит, mono
            yield bytes(buf)
            buf.clear()