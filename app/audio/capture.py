"""
Для Windows: запускаем winloopcap.exe (WASAPI-loopback) и
получаем stdout-поток PCM 48 кГц 16-bit mono.

Для Linux/macOS остаётся fallback на sounddevice (см. функции внизу).
"""
from __future__ import annotations
import asyncio, os, sys, platform, shutil, itertools, subprocess
from pathlib import Path
from typing import AsyncGenerator, Generator

RATE  = 48_000
CHUNK = 1_024                 # 1024 * 2 байта = 2 KiB на кадр

# ───────────── Windows (winloopcap.exe) ──────────────
async def _win_stream() -> AsyncGenerator[bytes, None]:
    exe = shutil.which("winloopcap.exe") or str(Path(__file__).parent / "winloopcap.exe")
    if not Path(exe).exists():
        raise RuntimeError("winloopcap.exe not найден. Скомпилируйте capture-cli или положите рядом.")

    # запускаем без аргументов → пишет бесконечно
    proc = await asyncio.create_subprocess_exec(
        exe, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        while True:
            chunk = await proc.stdout.read(CHUNK * 2)  # 2 bytes per sample
            if not chunk:
                break
            yield chunk
    finally:
        proc.terminate()
        await proc.wait()

# ───────────── Fallback для других ОС (PortAudio) ─────
def _other_stream() -> Generator[bytes, None, None]:
    import numpy as np, sounddevice as sd

    RATE  = 48_000
    CHUNK = 1_024
    dev   = sd.default.device[1]
    channels = max(sd.query_devices(dev)["max_output_channels"], 2)

    with sd.InputStream(
        samplerate=RATE, blocksize=CHUNK, dtype="int16",
        channels=channels, device=dev, extra_settings=sd.WasapiSettings(loopback=True)
    ) as s:
        while True:
            frames, _ = s.read(CHUNK)
            mono = frames.astype(np.int32).mean(axis=1).astype("int16").tobytes()
            yield mono

# ───────────── Public helpers ──────────────
async def stream_async() -> AsyncGenerator[bytes, None]:
    if platform.system() == "Windows":
        async for chunk in _win_stream():
            yield chunk
    else:
        for chunk in _other_stream():
            yield chunk
            await asyncio.sleep(0)          # cooperative

async def capture_minutes(minutes: int) -> bytes:
    total_samples = minutes * 60 * RATE
    grabbed = bytearray()
    async for chunk in stream_async():
        grabbed.extend(chunk)
        if len(grabbed) // 2 >= total_samples:   # 2 bytes per sample
            break
    return bytes(grabbed)
