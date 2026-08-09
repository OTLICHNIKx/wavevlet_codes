import csv
import os
from time import perf_counter
from typing import Any, Callable

import numpy as np

from decode.syndrome_decoding import (
    CompactSyndromeTable,
    build_compact_syndrome_table,
)
from modulation.demodulator import (
    bpsk_llr,
    hard_decision_from_llr,
    reliability_from_llr,
)

from research.code_factory import build_code_from_config

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

def get_syndrome_t_for_code(
    code_config: CodeResearchConfig,
    decoder_config: DecoderResearchConfig,
) -> int:
    """
    Возвращает t для синдромного декодирования.
    """
    if code_config.syndrome_max_error_weight is not None:
        return code_config.syndrome_max_error_weight

    return decoder_config.syndrome_max_error_weight


def get_chase_inner_t_for_code(
    code_config: CodeResearchConfig,
    decoder_config: DecoderResearchConfig,
) -> int:
    """
    Возвращает t внутреннего синдромного декодера в алгоритме Чейза.
    """
    if code_config.chase_inner_decoder_max_error_weight is not None:
        return code_config.chase_inner_decoder_max_error_weight

    return decoder_config.chase_inner_decoder_max_error_weight

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


SyndromeTable = CompactSyndromeTable


def build_syndrome_table_cache(
    parity_check_matrix: np.ndarray,
    code_config: CodeResearchConfig,
    decoder_config: DecoderResearchConfig,
) -> tuple[dict[int, SyndromeTable], dict[int, float]]:
    """
    Один раз строит таблицы синдромов, необходимые для кода.

    Таблица зависит только от H и максимального веса t, поэтому
    её не нужно перестраивать для каждой точки Eb/N0. Если syndrome
    и Chase используют одинаковый t, они совместно используют одну
    и ту же таблицу.
    """
    required_weights: set[int] = set()

    if decoder_config.run_syndrome:
        required_weights.add(
            get_syndrome_t_for_code(
                code_config=code_config,
                decoder_config=decoder_config,
            )
        )

    if decoder_config.run_chase:
        required_weights.add(
            get_chase_inner_t_for_code(
                code_config=code_config,
                decoder_config=decoder_config,
            )
        )

    tables: dict[int, SyndromeTable] = {}
    build_times: dict[int, float] = {}

    for max_error_weight in sorted(required_weights):
        start_time = perf_counter()
        tables[max_error_weight] = build_compact_syndrome_table(
            parity_check_matrix=parity_check_matrix,
            max_error_weight=max_error_weight,
        )
        build_times[max_error_weight] = perf_counter() - start_time

    return tables, build_times


def run_decoders_for_channel_output(
    received_words: np.ndarray,
    received_symbols: np.ndarray,
    reliability: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: np.ndarray,
    code_config: CodeResearchConfig,
    decoder_config: DecoderResearchConfig,
    syndrome_tables: dict[int, SyndromeTable] | None = None,
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

    syndrome_t = get_syndrome_t_for_code(
        code_config=code_config,
        decoder_config=decoder_config,
    )

    chase_inner_t = get_chase_inner_t_for_code(
        code_config=code_config,
        decoder_config=decoder_config,
    )

    if decoder_config.run_syndrome:
        results.append(
            syndrome_decode_batch(
                received_words=received_words,
                parity_check_matrix=parity_check_matrix,
                generator_matrix=generator_matrix,
                max_error_weight=syndrome_t,
                syndrome_table=(
                    None
                    if syndrome_tables is None
                    else syndrome_tables.get(syndrome_t)
                ),
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
                inner_decoder_max_error_weight=chase_inner_t,
                syndrome_table=(
                    None
                    if syndrome_tables is None
                    else syndrome_tables.get(chase_inner_t)
                ),
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
    syndrome_table_build_time_sec: float = 0.0,
    syndrome_table: SyndromeTable | None = None,
) -> dict[str, Any]:
    """
    Преобразует результат декодера и метрики в строку summary.csv.
    """
    base_row: dict[str, Any] = {
        "code_name": code_config.name,
        "code_family": code_config.family,

        "n": code_config.n,
        "k": code_config.k,
        "code_rate": code_config.k / code_config.n,

        "h": (
            ""
            if code_config.h is None
            else " ".join(
                str(value)
                for value in code_config.h
            )
        ),

        "g": (
            ""
            if code_config.g is None
            else " ".join(
                str(value)
                for value in code_config.g
            )
        ),

        "bch_m": (
            ""
            if code_config.bch_m is None
            else code_config.bch_m
        ),

        "bch_designed_distance": (
            ""
            if code_config.bch_designed_distance is None
            else code_config.bch_designed_distance
        ),

        "bch_first_root": (
            ""
            if code_config.family not in ("bch", "bch_derived")
            else code_config.bch_first_root
        ),

        "bch_primitive_polynomial": (
            ""
            if code_config.bch_primitive_polynomial is None
            else code_config.bch_primitive_polynomial
        ),

        "bch_shortening_count": (
            code_config.bch_shortening_count
        ),
        "bch_puncture_count": (
            code_config.bch_puncture_count
        ),

        "expected_min_distance": (
            ""
            if code_config.expected_min_distance is None
            else code_config.expected_min_distance
        ),

        "syndrome_t": (
            ""
            if code_config.syndrome_max_error_weight is None
            else code_config.syndrome_max_error_weight
        ),

        "chase_inner_t": (
            ""
            if (
                    code_config
                    .chase_inner_decoder_max_error_weight
                    is None
            )
            else (
                code_config
                .chase_inner_decoder_max_error_weight
            )
        ),

        "chase_p": (
            ""
            if (
                    code_config
                    .chase_unreliable_positions_count
                    is None
            )
            else (
                code_config
                .chase_unreliable_positions_count
            )
        ),

        "ebn0_db": ebn0_db,
        "sigma": sigma,
        "message_count": message_count,
        "decoder": decoder_result.decoder_name,
        "skipped": decoder_result.skipped,
        "skip_reason": decoder_result.skip_reason or "",
        "syndrome_table_build_time_sec": syndrome_table_build_time_sec,
        "syndrome_table_pattern_count": (
            "" if syndrome_table is None else syndrome_table.pattern_count
        ),
        "syndrome_table_entry_count": (
            "" if syndrome_table is None else syndrome_table.entry_count
        ),
        "syndrome_table_collision_count": (
            "" if syndrome_table is None else syndrome_table.collision_count
        ),
        "syndrome_table_memory_bytes": (
            "" if syndrome_table is None else syndrome_table.approx_memory_bytes
        ),
    }

    if metrics is None:
        base_row.update(
            {
                "bit_errors": "",
                "total_bits": "",
                "ber": "",
                "pessimistic_ber": "",
                "ber_on_success": "",
                "success_count": "",
                "successful_decoded_bits": "",
                "bit_errors_on_success": "",
                "frame_errors": "",
                "frame_error_rate": "",
                "codeword_errors": "",
                "codeword_error_rate": "",
                "failure_count": "",
                "failure_rate": "",
                "miscorrection_count": "",
                "miscorrection_rate": "",
                "conditional_miscorrection_rate": "",
                "ambiguous_count": "",
                "ambiguous_rate": "",
                "total_time_sec": "",
                "avg_time_ms": "",
                "average_decoding_time_ms": "",
            }
        )
        return base_row

    base_row.update(
        {
            "bit_errors": metrics.bit_errors,
            "total_bits": metrics.total_bits,
            "ber": metrics.ber,
            "pessimistic_ber": metrics.pessimistic_ber,
            "ber_on_success": (
                "" if metrics.ber_on_success is None else metrics.ber_on_success
            ),
            "success_count": metrics.success_count,
            "successful_decoded_bits": metrics.successful_decoded_bits,
            "bit_errors_on_success": metrics.bit_errors_on_success,
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
            "miscorrection_count": metrics.miscorrection_count,
            "miscorrection_rate": metrics.miscorrection_rate,
            "conditional_miscorrection_rate": (
                ""
                if metrics.conditional_miscorrection_rate is None
                else metrics.conditional_miscorrection_rate
            ),
            "ambiguous_count": metrics.ambiguous_count,
            "ambiguous_rate": metrics.ambiguous_rate,
            "total_time_sec": metrics.total_time_sec,
            "avg_time_ms": metrics.avg_time_ms,
            "average_decoding_time_ms": metrics.avg_time_ms,
        }
    )

    return base_row


def _emit_progress(
    callback: Callable[[dict], None] | None,
    payload: dict,
) -> None:
    """Отправляет прогресс наружу; ошибки колбэка не должны ломать расчёт."""
    if callback is None:
        return
    try:
        callback(payload)
    except Exception:  # noqa: BLE001
        pass


def run_code_research(
    code_config: CodeResearchConfig,
    dataset: CodeResearchDataset,
    decoder_config: DecoderResearchConfig,
    ebn0_db_values: tuple[float, ...],
    progress_callback: Callable[[dict], None] | None = None,
) -> list[dict[str, Any]]:
    """
    Запускает исследование для одного кода на всех Eb/N0.
    """
    print()
    print(
        f"Код {code_config.name} "
        f"[{code_config.family}]: "
        f"n={code_config.n}, k={code_config.k}"
    )

    decoders_planned = sum(
        1
        for enabled in (
            decoder_config.run_syndrome,
            decoder_config.run_hard_mld,
            decoder_config.run_soft_mld,
            decoder_config.run_chase,
        )
        if enabled
    )

    _emit_progress(
        progress_callback,
        {
            "stage": "code_started",
            "code": code_config.name,
            "family": code_config.family,
            "n": code_config.n,
            "k": code_config.k,
            "ebn0_point_count": len(ebn0_db_values),
            "planned_decoders": decoders_planned,
        },
    )

    code = build_code_from_config(code_config)

    messages = dataset.messages
    base_noise = dataset.base_noise

    codewords = encode_messages_batch(
        messages=messages,
        generator_matrix=code.generator_matrix,
    )

    transmitted_symbols = bpsk_modulate_batch(codewords)

    parity_check_matrix = code.parity_check_matrix
    generator_matrix = code.generator_matrix

    syndrome_tables, syndrome_table_build_times = build_syndrome_table_cache(
        parity_check_matrix=parity_check_matrix,
        code_config=code_config,
        decoder_config=decoder_config,
    )

    for table_t, build_time in syndrome_table_build_times.items():
        table = syndrome_tables[table_t]
        memory_mib = table.approx_memory_bytes / (1024 ** 2)
        print(
            f"  Компактная таблица синдромов t={table_t}: "
            f"{table.entry_count} синдромов / "
            f"{table.pattern_count} шаблонов, "
            f"коллизий {table.collision_count}, "
            f"~{memory_mib:.2f} MiB, "
            f"построение {build_time:.3f}s"
        )

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
            syndrome_tables=syndrome_tables,
        )

        decoders_finished = 0

        syndrome_t = get_syndrome_t_for_code(
            code_config=code_config,
            decoder_config=decoder_config,
        )
        chase_inner_t = get_chase_inner_t_for_code(
            code_config=code_config,
            decoder_config=decoder_config,
        )

        for decoder_result in decoder_results:
            table_build_time = 0.0
            decoder_syndrome_table: SyndromeTable | None = None

            if decoder_result.decoder_name == "syndrome":
                table_build_time = syndrome_table_build_times.get(syndrome_t, 0.0)
                decoder_syndrome_table = syndrome_tables.get(syndrome_t)
            elif decoder_result.decoder_name == "chase":
                table_build_time = syndrome_table_build_times.get(chase_inner_t, 0.0)
                decoder_syndrome_table = syndrome_tables.get(chase_inner_t)
            if decoder_result.skipped:
                row = decoder_result_to_summary_row(
                    code_config=code_config,
                    ebn0_db=ebn0_db,
                    sigma=sigma,
                    decoder_result=decoder_result,
                    metrics=None,
                    message_count=len(messages),
                    syndrome_table_build_time_sec=table_build_time,
                    syndrome_table=decoder_syndrome_table,
                )
                rows.append(row)
                print(f"    {decoder_result.decoder_name}: skipped")

                decoders_finished += 1
                _emit_progress(
                    progress_callback,
                    {
                        "stage": "running",
                        "code": code_config.name,
                        "ebn0_db": float(ebn0_db),
                        "decoder": decoder_result.decoder_name,
                        "skipped": True,
                        "completed_decoders": decoders_finished,
                        "planned_decoders": decoders_planned,
                    },
                )
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
                syndrome_table_build_time_sec=table_build_time,
                syndrome_table=decoder_syndrome_table,
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

            decoders_finished += 1
            _emit_progress(
                progress_callback,
                {
                    "stage": "running",
                    "code": code_config.name,
                    "ebn0_db": float(ebn0_db),
                    "decoder": decoder_result.decoder_name,
                    "skipped": False,
                    "ber": metrics.ber,
                    "fer": metrics.frame_error_rate,
                    "failure_rate": metrics.failure_rate,
                    "completed_decoders": decoders_finished,
                    "planned_decoders": decoders_planned,
                },
            )

        _emit_progress(
            progress_callback,
            {
                "stage": "ebn0_finished",
                "code": code_config.name,
                "ebn0_db": float(ebn0_db),
                "decoders_finished": decoders_finished,
            },
        )

    _emit_progress(
        progress_callback,
        {
            "stage": "code_finished",
            "code": code_config.name,
        },
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


def run_research(
    config: ResearchConfig,
    progress_callback: Callable[[dict], None] | None = None,
) -> list[dict[str, Any]]:
    """
    Полный запуск исследования.
    """
    print("Запуск исследования декодеров")
    print("-" * 70)
    print("Количество сообщений:", config.message_count)
    print("Eb/N0 values:", config.ebn0_db_values)
    print("Результаты:", config.results_dir)

    total_units = (
        len(config.codes)
        * len(config.ebn0_db_values)
        * sum(
            1
            for enabled in (
                config.decoders.run_syndrome,
                config.decoders.run_hard_mld,
                config.decoders.run_soft_mld,
                config.decoders.run_chase,
            )
            if enabled
        )
    )
    completed_units = 0

    def _tracking_callback(payload: dict) -> None:
        nonlocal completed_units

        if (
            payload.get("stage") == "running"
            and "decoder" in payload
        ):
            completed_units += 1
            enriched = {
                **payload,
                "completed": completed_units,
                "total": total_units,
            }
        else:
            enriched = {
                "completed": completed_units,
                "total": total_units,
                **payload,
            }

        _emit_progress(progress_callback, enriched)

    _emit_progress(
        progress_callback,
        {
            "stage": "validating",
            "codes": [c.name for c in config.codes],
            "ebn0_db_values": list(config.ebn0_db_values),
            "message_count": config.message_count,
            "completed": 0,
            "total": total_units,
        },
    )

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
            progress_callback=_tracking_callback,
        )

        all_rows.extend(rows)

    output_path = os.path.join(config.results_dir, "summary.csv")

    write_summary_csv(
        rows=all_rows,
        output_path=output_path,
    )

    _emit_progress(
        progress_callback,
        {
            "stage": "writing_results",
            "output_path": output_path,
            "completed": completed_units,
            "total": total_units,
        },
    )

    print()
    print("Исследование завершено.")
    print("Файл результатов:", output_path)

    return all_rows
