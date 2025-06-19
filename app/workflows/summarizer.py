from __future__ import annotations
import asyncio, json, os, re, tempfile, textwrap, wave, aiohttp, subprocess

import whisper
MODEL_FULL = whisper.load_model("large-v2")

# ────────── fast chunk ASR (live subtitles) ──────────
async def stt_chunk(pcm: bytes) -> str:
    """быстрый неполный прогон для live-субтитров – tiny модель в памяти"""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: whisper.transcribe.model.transcribe_tiny(pcm))
    return result["text"]

# ────────── full ASR ─────────────────────────────────
async def stt(pcm: bytes) -> str:
    loop = asyncio.get_running_loop()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(48_000); wf.writeframes(pcm)
        path = tmp.name
    try:
        res = await loop.run_in_executor(None, lambda: MODEL_FULL.transcribe(path, language="ru"))
        return res["text"]
    finally:
        os.remove(path)

# ────────── summarization ───────────────────────────
async def summarize(text: str, *, model: str, style: str) -> str:
    prompt_style = {
        "bullet":   "Сформулируй в виде маркированного списка:\n- пункт 1\n- пункт 2\n",
        "letter":   "Напиши краткое письмо-резюме для коллег, пропустивших встречу.\n",
        "protocol": "Составь детальный протокол (вопрос, решение, ответственный).\n",
    }[style]

    prompt = textwrap.dedent(f"""{prompt_style}
        Добавляй к каждому пункту тайм-код в формате [мм:сс], где мм:сс — приблизительное место фразы в оригинале.
        Текст стенограммы:
        {text[:20000]}
    """)

    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "stream": False, "prompt": prompt},
                timeout=aiohttp.ClientTimeout(total=900),
            ) as r:
                data = await r.json()
        except aiohttp.ClientConnectionError as e:
            raise RuntimeError("Ollama не запущен.") from e

    if "error" in data:
        raise RuntimeError(data["error"])

    response = data.get("response") or ""
    response = re.sub(r"<think>.*?</think>", "", response, flags=re.S)
    # заменяем plain-таймкоды на кликабельный вид ▶ 00:12
    response = re.sub(r"\[(\d{1,2}:\d{2})\]", r"▶ \1", response)
    return response
