import json
import pathlib

p = pathlib.Path("research_results/code_optimization")

# Переименовываем артефакт фазы with-points (он перезаписал файл фазы 1).
withpoints = p / "rs_32_16_candidates.json"
target = p / "rs_32_16_candidates_phase2_withpoints.json"
if withpoints.exists():
    withpoints.rename(target)

provenance = {
    "family": "reed_solomon_binary",
    "n": 32,
    "k": 16,
    "runs": [
        {
            "phase": "1 (column multipliers only, points fixed 0..7)",
            "script": "python -m research.optimization.optimize_rs_32_16 "
                      "--time-limit 1200 --chains 3 --seed 420",
            "evaluations": 22571,
            "best": {
                "d_min_exact": 7,
                "A_dmin": 28,
                "column_multipliers": [4, 6, 13, 7, 8, 12, 15, 10],
                "evaluation_points": [0, 1, 2, 3, 4, 5, 6, 7],
                "fingerprint": "e0f4d1f05cc196bb",
            },
            "note": "artifact overwritten by phase 2 run; the winner is "
                    "re-verified independently in verification.json "
                    "(exact 2^16 enumeration of the production config)",
        },
        {
            "phase": "2 (multipliers + evaluation points)",
            "script": "python -m research.optimization.optimize_rs_32_16 "
                      "--time-limit 600 --chains 2 --seed 99000 --with-points",
            "evaluations": 11673,
            "best": {
                "d_min_exact": 7,
                "A_dmin": 45,
                "column_multipliers": [12, 4, 14, 13, 13, 5, 12, 4],
                "evaluation_points": [8, 3, 13, 7, 4, 14, 6, 12],
                "fingerprint": "86185d9ccee8278a",
            },
            "note": "no improvement beyond d=7; A_d worse than phase 1; "
                    "phase 1 winner retained",
        },
    ],
    "decision": "integrated phase 1 winner (d=7, A_7=28) into "
                "REED_SOLOMON_32_16_CONFIG",
}
(p / "rs_32_16_provenance.json").write_text(
    json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("provenance written")
