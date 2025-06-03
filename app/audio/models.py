from dataclasses import dataclass

@dataclass(slots=True)
class Frame:
    data: bytes  # raw PCM int16 mono