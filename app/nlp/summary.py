import aiohttp, asyncio, textwrap
from ..config import settings


aSYNC_TIMEOUT = aiohttp.ClientTimeout(total=300)

async def summarize(transcript: str) -> str:
    prompt = textwrap.dedent(f"""
    Составь компактное (не более 15 строк) резюме стенограммы онлайн‑совещания, обязательно перечисли
    принятые решения и назначенных ответственных. Текст стенограммы:
    """ + transcript)

    async with aiohttp.ClientSession(timeout=aSYNC_TIMEOUT) as sess:
        async with sess.post(
            f"{settings.ollama_host}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
        ) as resp:
            data = await resp.json()
    return data.get("response", "")