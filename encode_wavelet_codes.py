"""
Устаревший путь импорта.

Основная реализация перенесена в:

    wavelet.encoder

Файл временно оставлен для совместимости со старыми скриптами.
"""

from wavelet.encoder import (
    build_wavelet_code_for_message,
    encode_wavelet_message,
    ensure_binary_vector,
)

__all__ = [
    "build_wavelet_code_for_message",
    "encode_wavelet_message",
    "ensure_binary_vector",
]