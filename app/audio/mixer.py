import numpy as np


def mix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Averages two mono int16 numpy arrays, prevents clipping."""
    return ((a.astype(np.int32) + b.astype(np.int32)) // 2).astype(np.int16)


def normalize(signal: np.ndarray, target_peak: int = 30000) -> np.ndarray:
    """Simple peak normalization to `target_peak` (≤ 32767)."""
    peak = np.abs(signal).max() or 1
    gain = target_peak / peak
    out = (signal.astype(np.float32) * gain).clip(-32768, 32767).astype(np.int16)
    return out