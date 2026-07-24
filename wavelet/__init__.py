"""
Пакет реализации линейных вейвлет-кодов.

Основные публичные объекты:

    WaveletCode
    build_wavelet_generator_matrix
    build_wavelet_parity_check_matrix
    encode_wavelet_message
"""

from .code import (
    WaveletCode,
    build_cyclic_filter_matrix,
    build_detail_coefficients,
    build_inverse_wavelet_matrices,
    build_shift_matrix,
    build_wavelet_generator_matrix,
    build_wavelet_parity_check_matrix,
    check_wavelet_inverse_conditions,
    gf_inverse_matrix,
    gf_matmul,
    gf_rank,
    to_field_matrix,
    to_field_vector,
)

from .encoder import (
    build_wavelet_code_for_message,
    encode_wavelet_message,
    ensure_binary_vector,
)

__all__ = [
    "WaveletCode",
    "build_cyclic_filter_matrix",
    "build_detail_coefficients",
    "build_inverse_wavelet_matrices",
    "build_shift_matrix",
    "build_wavelet_generator_matrix",
    "build_wavelet_parity_check_matrix",
    "check_wavelet_inverse_conditions",
    "gf_inverse_matrix",
    "gf_matmul",
    "gf_rank",
    "to_field_matrix",
    "to_field_vector",
    "build_wavelet_code_for_message",
    "encode_wavelet_message",
    "ensure_binary_vector",
]