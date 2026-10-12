"""Этап 0: манифест v1 — фиксация исходных результатов и конфигураций.

Собирает:
  * версии Python/NumPy и git-commit;
  * список legacy-каталогов v1 с размерами и контрольными суммами;
  * по каждому эксперименту — коды, каналы, сетки Eb/N0, декодеры, t/p,
    seed, слова, сиды, skipped;
  * контрольные суммы (sha256) матриц G/H всех использованных кодов;
  * известные пробелы/неопределённости.

Результат: research_results/v2_validation/v1_manifest.json
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "research_results" / "v2_validation"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True,
            cwd=str(ROOT),
        ).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"<git error: {exc}>"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _matrices_hash(code) -> dict[str, str]:
    G = np.asarray(code.generator_matrix, dtype=np.uint8)
    H = np.asarray(code.parity_check_matrix, dtype=np.uint8)
    return {
        "G_sha256": hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest(),
        "H_sha256": hashlib.sha256(np.ascontiguousarray(H).tobytes()).hexdigest(),
        "G_shape": list(G.shape),
        "H_shape": list(H.shape),
        "G_weight": int(G.sum()),
        "H_weight": int(H.sum()),
    }


def _scan_dir(base: Path) -> list[dict]:
    items = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            items.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256_file(path)
                    if path.suffix in (".csv", ".json")
                    else "<not hashed>",
                }
            )
    return items


def _mc_settings(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "settings": data.get("settings"),
        "codes": data.get("codes"),
        "channels": data.get("channels"),
        "decoders": data.get("decoders"),
        "channel_params": data.get("channel_params"),
        "seed_scheme": data.get("seed_scheme"),
        "note_mld": data.get("note_mld"),
    }


def main() -> None:
    from research.config import _load_preset
    from research.code_factory import build_code_from_config

    # --- контрольные суммы кодов из пресетов v1 ---
    code_names = [
        "WAVELET_16_8_CONFIG", "BCH_DERIVED_16_8_CONFIG",
        "GOPPA_16_8_CONFIG", "REED_SOLOMON_16_8_CONFIG", "LDPC_16_8_CONFIG",
        "WAVELET_32_16_CONFIG", "BCH_DERIVED_32_16_CONFIG",
        "GOPPA_32_16_CONFIG", "REED_SOLOMON_32_16_CONFIG", "LDPC_32_16_CONFIG",
        "WAVELET_64_32_CONFIG", "BCH_DERIVED_64_32_CONFIG",
        "GOPPA_64_32_CONFIG", "REED_SOLOMON_64_32_CONFIG", "LDPC_64_32_CONFIG",
    ]
    codes_hash: dict[str, dict] = {}
    for name in code_names:
        try:
            cfg = _load_preset(name)
            code = build_code_from_config(cfg)
            codes_hash[name] = {
                "name": cfg.name,
                "family": cfg.family,
                "n": cfg.n,
                "k": cfg.k,
                "syndrome_t": cfg.syndrome_max_error_weight,
                "chase_inner_t": cfg.chase_inner_decoder_max_error_weight,
                "chase_p": cfg.chase_unreliable_positions_count,
                "d_exact": cfg.minimum_distance_exact,
                **_matrices_hash(code),
            }
        except Exception as exc:  # noqa: BLE001
            codes_hash[name] = {"error": str(exc)}

    # --- пресеты 100k (все каналы/размеры) ---
    exp_100k = {}
    for size in ("16_8", "32_16", "64_32"):
        exp_100k[size] = {}
        for ch in ("", "_RAYLEIGH", "_RAYLEIGH_AWGN", "_SINUSOIDAL"):
            pname = f"FIVE_FAMILIES_1K_FULL_DECODERS_{size}{ch}"
            try:
                cfg = _load_preset(pname)
                exp_100k[size][ch or "awgn"] = {
                    "preset": pname,
                    "channel_type": cfg.channel_type,
                    "message_count_preset": cfg.message_count,
                    "ebn0_db_values_preset": list(cfg.ebn0_db_values),
                    "decoders": cfg.decoders.to_json_dict(),
                    "codes": [c.name for c in cfg.codes],
                }
            except Exception as exc:  # noqa: BLE001
                exp_100k[size][ch or "awgn"] = {"error": str(exc)}

    # --- fair_t 64_32 (фактический прогон 03.10) ---
    fair = {}
    for ch in ("RAYLEIGH", "RAYLEIGH_AWGN", "SINUSOIDAL"):
        pname = f"FIVE_FAMILIES_64_32_FAIR_T_{ch}"
        try:
            cfg = _load_preset(pname)
            fair[ch] = {
                "preset": pname,
                "channel_type": cfg.channel_type,
                "message_count": cfg.message_count,
                "ebn0_db_values": list(cfg.ebn0_db_values),
                "codes": [
                    {
                        "name": c.name,
                        "n": c.n, "k": c.k,
                        "t": c.syndrome_max_error_weight,
                        "inner_t": c.chase_inner_decoder_max_error_weight,
                        "p": c.chase_unreliable_positions_count,
                    }
                    for c in cfg.codes
                ],
            }
        except Exception as exc:  # noqa: BLE001
            fair[ch] = {"error": str(exc)}

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "git_commit": _git("rev-parse", "HEAD"),
            "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "git_status_short": _git("status", "--short"),
        },
        "legacy_dirs": {
            "legacy_100k": _scan_dir(ROOT / "research_results" / "legacy_100k"),
            "legacy_mc/mc_full_50seeds": _scan_dir(
                ROOT / "research_results" / "legacy_mc" / "mc_full_50seeds"
            ),
            "legacy_mc/mc_fair_t_64_32": _scan_dir(
                ROOT / "research_results" / "legacy_mc" / "mc_fair_t_64_32"
            ),
        },
        "code_matrix_checksums": codes_hash,
        "scenario_100k_presets": exp_100k,
        "scenario_fair_t_64_32": fair,
        "scenario_mc_full_50seeds": _mc_settings(
            ROOT / "research_results" / "mc_full_50seeds"
            / "experiment_config.json"
        ),
        "scenario_mc_fair_t_64_32": _mc_settings(
            ROOT / "research_results" / "mc_fair_t_64_32"
            / "experiment_config.json"
        ),
        "notes": [
            "100k-прогон фактически сделан с message_count=100000 и сеткой "
            "0..5 dB шаг 0.5 (presets FIVE_FAMILIES_1K_*).",
            "64/32 в five_families_full_100k/*/64_32_100k — это FAIR_T прогон "
            "(wavelet/goppa t=5, остальные t=4, сетка 0..12 dB, 18 точек); "
            "старые t=4 версии — в 64_32_100k_t4_backup.",
            "MC full 50 seeds: 15 кодов, сетка 0..6 dB, 50 seeds x 1000 слов.",
            "MC fair_t 64_32: 5 кодов, сетка 0..12 dB (18 точек), 50 seeds x 1000.",
            "BER-столбец 'ber' в v1 = pessimistic (отказ = k битовых ошибок); "
            "наблюдаемый BER восстановленных битов — отдельно в ber_on_success.",
            "d_min для 64/32 уточнён полным MITM-перебором в отдельной сессии; "
            "точные значения записаны в metadata кодов FAIR_T-пресетов.",
        ],
    }

    out = OUT_DIR / "v1_manifest.json"
    out.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("written", out)


if __name__ == "__main__":
    main()