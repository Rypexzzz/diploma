from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    whisper_model_size: str = "large-v2"  # tiny|base|small|medium|large|large-v2
    sample_rate: int = 48_000
    chunk: int = 1024  # сэмплов
    record_dir: Path = Path.home() / "Documents/OMO"

    ollama_host: str = "http://localhost:11434"  # deepseek-v3 работает здесь
    ollama_model: str = "deepseek-v3:32b"

settings = Settings()