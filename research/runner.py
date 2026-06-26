import csv
import os
from dataclasses import asdict
from typing import Any

import numpy as np

from encode_wavelet_codes import encode_wavelet_message
from modulation.demodulator import (
    bpsk_llr,
    hard_decision_from_llr,
    reliability_from_llr,
)
from research.config import (
    CodeResearchConfig,
    DecoderResearchConfig,
    ResearchConfig,
)
from research.dataset import (
    CodeResearchDataset,
    apply_awgn_from_base_noise,
    build_all_datasets,
    ebn0_db_to_sigma,
)
from research.decoder_wrappers import (
    DecoderBatchResult,
    chase_decode_batch,
    hard_mld_decode_batch,
    soft_mld_decode_batch,
    syndrome_decode_batch,
)
from research.metrics import BatchMetrics, calculate_batch_metrics


def encode_messages_batch(
    messages: np.ndarray,
    generator_matrix: np.ndarray,
) -> np.ndarray:
    """
    Пакетное кодирование сообщений.

    messages:
        матрица размера message_count x k

    generator_matrix:
        порождающая матрица размера k x n

    Возвращает:
        codewords размера message_count x n
    """
    messages = np.asarray(messages, dtype=np.uint8)
    generator_matrix = np.asarray(generator_matrix, dtype=np.uint8)

    if messages.ndim != 2:
        raise ValueError("messages должен быть двумерной матрицей")

    if generator_matrix.ndim != 2:
        raise ValueError("generator_matrix должна быть двумерной матрицей")

    if messages.shape[1] != generator_matrix.shape[0]:
        raise ValueError(
            "Количество столбцов messages должно совпадать "
            "с количеством строк generator_matrix"
        )

    return ((messages @ generator_matrix) % 2).astype(np.uint8)


def bpsk_modulate_batch(codewords: np.ndarray) -> np.ndarray:
    """
    Пакетная BPSK-модуляция.

    Правило:
        0 -> +1
        1 -> -1
    """
    codewords = np.asarray(codewords, dtype=np.uint8)

    if codewords.ndim != 2:
        raise ValueError("codewords должен быть двумерной матрицей")

    if not np.all((codewords == 0) | (codewords == 1)):
        raise ValueError("codewords должен содержать только 0 и 1")

    return 1.0 - 2.0 * codewords


def build_code_from_config(code_config: CodeResearchConfig):
    """
    Строит WaveletCode по настройкам исследуемого кода.
    """
    dummy_message = np.zeros(code_config.k, dtype=np.uint8)

    code, _ = encode_wavelet_message(
        h=code_config.h,
        message=dummy_message,
        a=code_config.a,
        shift=code_config.shift,
    )

    if code.n != code_config.n:
        raise ValueError(
            f"Ожидалась длина кода n = {code_config.n}, "
            f"но построен код n = {code.n}"
        )

    if code.k != code_config.k:
        raise ValueError(
            f"Ожидалась размерность k = {code_config.k}, "
            f"но построен код k = {code.k}"
        )

    return code


def make_skipped_decoder_result(
    decoder_name: str,
    message_count: int,
    k: int,
    n: int,
    reason: str,
) -> DecoderBatchResult:
    """
    Создаёт результат для декодера, который был пропущен.
    """
    return DecoderBatchResult(
        decoder_name=decoder_name,
        decoded_messages=np.zeros((message_count, k), dtype=np.uint8),
        decoded_codewords=np.zeros((message_count, n), dtype=np.uint8),
        success_flags=np.zeros(message_count, dtype=bool),
        ambiguous_flags=np.zeros(message_count, dtype=bool),
        total_time_sec=0.0,
        skipped=True,
        skip_reason=reason,
    )

def get_chase_p_for_code(
    code_config: CodeResearchConfig,
    decoder_config: DecoderResearchConfig,
) -> int:
    """
    Возвращает число наименее надёжных позиций p для алгоритма Чейза.

    Если для конкретного кода задано своё значение, используем его.
    Иначе используем общее значение из DecoderResearchConfig.
    """
    if code_config.chase_unreliable_positions_count is not None:
        return code_config.chase_unreliable_positions_count

    return decoder_config.chase_unreliable_positions_count


def run_decoders_for_channel_output(
    received_words: np.ndarray,
    received_symbols: np.ndarray,
    reliability: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: np.ndarray,
    code_config: CodeResearchConfig,
    decoder_config: DecoderResearchConfig,
) -> list[DecoderBatchResult]:
    """
    Запускает все включённые декодеры для одного кода и одного Eb/N0.
    """
    message_count, n = received_words.shape
    k = generator_matrix.shape[0]

    results: list[DecoderBatchResult] = []

    chase_p = get_chase_p_for_code(
        code_config=code_config,
        decoder_config=decoder_config,
    )

    if decoder_config.run_syndrome:
        results.append(
            syndrome_decode_batch(
                received_words=received_words,
                parity_check_matrix=parity_check_matrix,
                generator_matrix=generator_matrix,
                max_error_weight=decoder_config.syndrome_max_error_weight,
            )
        )

    if decoder_config.run_hard_mld:
        if k > decoder_config.max_k_for_mld:
            results.append(
                make_skipped_decoder_result(
                    decoder_name="hard_mld",
                    message_count=message_count,
                    k=k,
                    n=n,
                    reason=(
                        f"Пропущено: k = {k} больше max_k_for_mld = "
                        f"{decoder_config.max_k_for_mld}"
                    ),
                )
            )
        else:
            results.append(
                hard_mld_decode_batch(
                    received_words=received_words,
                    generator_matrix=generator_matrix,
                )
            )

    if decoder_config.run_soft_mld:
        if k > decoder_config.max_k_for_mld:
            results.append(
                make_skipped_decoder_result(
                    decoder_name="soft_mld",
                    message_count=message_count,
                    k=k,
                    n=n,
                    reason=(
                        f"Пропущено: k = {k} больше max_k_for_mld = "
                        f"{decoder_config.max_k_for_mld}"
                    ),
                )
            )
        else:
            results.append(
                soft_mld_decode_batch(
                    received_symbols=received_symbols,
                    generator_matrix=generator_matrix,
                )
            )

    if decoder_config.run_chase:
        results.append(
            chase_decode_batch(
                received_words=received_words,
                received_symbols=received_symbols,
                reliability=reliability,
                parity_check_matrix=parity_check_matrix,
                generator_matrix=generator_matrix,
                unreliable_positions_count=chase_p,
                inner_decoder_max_error_weight=decoder_config.chase_inner_decoder_max_error_weight,
            )
        )

    return results


def decoder_result_to_summary_row(
    code_config: CodeResearchConfig,
    ebn0_db: float,
    sigma: float,
    decoder_result: DecoderBatchResult,
    metrics: BatchMetrics | None,
    message_count: int,
) -> dict[str, Any]:
    """
    Преобразует результат декодера и метрики в строку summary.csv.
    """
    base_row: dict[str, Any] = {
        "code_name": code_config.name,
        "n": code_config.n,
        "k": code_config.k,
        "code_rate": code_config.k / code_config.n,
        "h": " ".join(str(value) for value in code_config.h),
        "ebn0_db": ebn0_db,
        "sigma": sigma,
        "message_count": message_count,
        "decoder": decoder_result.decoder_name,
        "skipped": decoder_result.skipped,
        "skip_reason": decoder_result.skip_reason or "",
    }

    if metrics is None:
        base_row.update(
            {
                "bit_errors": "",
                "total_bits": "",
                "ber": "",
                "frame_errors": "",
                "frame_error_rate": "",
                "codeword_errors": "",
                "codeword_error_rate": "",
                "failure_count": "",
                "failure_rate": "",
                "ambiguous_count": "",
                "ambiguous_rate": "",
                "total_time_sec": "",
                "avg_time_ms": "",
            }
        )
        return base_row

    base_row.update(
        {
            "bit_errors": metrics.bit_errors,
            "total_bits": metrics.total_bits,
            "ber": metrics.ber,
            "frame_errors": metrics.frame_errors,
            "frame_error_rate": metrics.frame_error_rate,
            "codeword_errors": (
                "" if metrics.codeword_errors is None else metrics.codeword_errors
            ),
            "codeword_error_rate": (
                ""
                if metrics.codeword_error_rate is None
                else metrics.codeword_error_rate
            ),
            "failure_count": metrics.failure_count,
            "failure_rate": metrics.failure_rate,
            "ambiguous_count": metrics.ambiguous_count,
            "ambiguous_rate": metrics.ambiguous_rate,
            "total_time_sec": metrics.total_time_sec,
            "avg_time_ms": metrics.avg_time_ms,
        }
    )

    return base_row


def run_code_research(
    code_config: CodeResearchConfig,
    dataset: CodeResearchDataset,
    decoder_config: DecoderResearchConfig,
    ebn0_db_values: tuple[float, ...],
) -> list[dict[str, Any]]:
    """
    Запускает исследование для одного кода на всех Eb/N0.
    """
    print()
    print(f"Код {code_config.name}: n={code_config.n}, k={code_config.k}")

    code = build_code_from_config(code_config)

    messages = dataset.messages
    base_noise = dataset.base_noise

    codewords = encode_messages_batch(
        messages=messages,
        generator_matrix=code.generator_matrix,
    )

    transmitted_symbols = bpsk_modulate_batch(codewords)

    parity_check_matrix = code.components["parity_check_matrix"]
    generator_matrix = code.generator_matrix

    rows: list[dict[str, Any]] = []

    for ebn0_db in ebn0_db_values:
        code_rate = code_config.k / code_config.n
        sigma = ebn0_db_to_sigma(
            ebn0_db=ebn0_db,
            code_rate=code_rate,
        )

        print(f"  Eb/N0 = {ebn0_db} dB, sigma = {sigma:.6f}")

        received_symbols = apply_awgn_from_base_noise(
            transmitted_symbols=transmitted_symbols,
            base_noise=base_noise,
            sigma=sigma,
        )

        llr = bpsk_llr(
            received_symbols=received_symbols,
            noise_std=sigma,
        )

        received_words = hard_decision_from_llr(llr)
        reliability = reliability_from_llr(llr)

        decoder_results = run_decoders_for_channel_output(
            received_words=received_words,
            received_symbols=received_symbols,
            reliability=reliability,
            parity_check_matrix=parity_check_matrix,
            generator_matrix=generator_matrix,
            code_config=code_config,
            decoder_config=decoder_config,
        )

        for decoder_result in decoder_results:
            if decoder_result.skipped:
                row = decoder_result_to_summary_row(
                    code_config=code_config,
                    ebn0_db=ebn0_db,
                    sigma=sigma,
                    decoder_result=decoder_result,
                    metrics=None,
                    message_count=len(messages),
                )
                rows.append(row)
                print(f"    {decoder_result.decoder_name}: skipped")
                continue

            metrics = calculate_batch_metrics(
                original_messages=messages,
                decoded_messages=decoder_result.decoded_messages,
                success_flags=decoder_result.success_flags,
                ambiguous_flags=decoder_result.ambiguous_flags,
                total_time_sec=decoder_result.total_time_sec,
                original_codewords=codewords,
                decoded_codewords=decoder_result.decoded_codewords,
            )

            row = decoder_result_to_summary_row(
                code_config=code_config,
                ebn0_db=ebn0_db,
                sigma=sigma,
                decoder_result=decoder_result,
                metrics=metrics,
                message_count=len(messages),
            )

            rows.append(row)

            print(
                f"    {decoder_result.decoder_name}: "
                f"BER={metrics.ber:.6f}, "
                f"FER={metrics.frame_error_rate:.6f}, "
                f"failure={metrics.failure_rate:.6f}, "
                f"ambiguous={metrics.ambiguous_rate:.6f}, "
                f"time={metrics.total_time_sec:.3f}s"
            )

    return rows


def write_summary_csv(
    rows: list[dict[str, Any]],
    output_path: str,
) -> None:
    """
    Сохраняет итоговую таблицу исследования в CSV.
    """
    if not rows:
        raise ValueError("Нет строк для сохранения")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = list(rows[0].keys())

    with open(output_path, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_research(config: ResearchConfig) -> list[dict[str, Any]]:
    """
    Полный запуск исследования.
    """
    print("Запуск исследования декодеров")
    print("-" * 70)
    print("Количество сообщений:", config.message_count)
    print("Eb/N0 values:", config.ebn0_db_values)
    print("Результаты:", config.results_dir)

    datasets = build_all_datasets(
        message_count=config.message_count,
        codes=config.codes,
        message_seed=config.message_seed,
        noise_seed=config.noise_seed,
    )

    all_rows: list[dict[str, Any]] = []

    for code_config in config.codes:
        dataset = datasets[code_config.name]

        rows = run_code_research(
            code_config=code_config,
            dataset=dataset,
            decoder_config=config.decoders,
            ebn0_db_values=config.ebn0_db_values,
        )

        all_rows.extend(rows)

    output_path = os.path.join(config.results_dir, "summary.csv")

    write_summary_csv(
        rows=all_rows,
        output_path=output_path,
    )

    print()
    print("Исследование завершено.")
    print("Файл результатов:", output_path)

    return all_rows