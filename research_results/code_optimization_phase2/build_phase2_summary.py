import json
import pathlib

p = pathlib.Path("research_results/code_optimization_phase2")
load = lambda name: json.loads((p / name).read_text(encoding="utf-8"))

baseline = load("baseline.json")
comparison = load("phase1_comparison.json")
bch = load("bch_phase2_candidates.json")
rs = load("rs_phase2_candidates.json")
goppa = load("goppa_phase2_candidates.json")
hyper = load("goppa_phase2_hyperplane.json")
verification = load("verification.json")

def cur(size_key, family):
    for e in baseline["phase2_start"][size_key]:
        if e["family"] == family:
            return e
    raise KeyError

summary = {
    "task": "CODE PARAMETER OPTIMIZATION — PHASE 2",
    "final_table": [
        {"code": "BCH 32,16", "baseline": 5, "phase1": 6, "phase2": 6,
         "improved_in_phase2": False,
         "reason": "629,440 точных puncture-оценок: все [34/35/40/43,16] "
                   "укорочения хранят >=34 слов веса 7, union их поддержек "
                   "покрывает проверочные координаты => после puncture>=2 "
                   "d=7 недостижим в перебранном пространстве "
                   "(m=6, dd in {7,9,11}, 7 представлений поля, extended-"
                   "варианты, 80 shortening-наборов на конфиг)"},
        {"code": "RS 32,16", "baseline": 6, "phase1": 7, "phase2": 7,
         "improved_in_phase2": False,
         "reason": "40,797 точных 2^16 оценок; обе базы GF(16) "
                   "(0b10011/0b11001), moves multipliers+points; все 6 "
                   "цепей сошлись к одному оптимуму (d=7, A_7=28, "
                   "fp e0f4d1f05cc196bb) — фаза 1 уже глобальный оптимум "
                   "в бюджете"},
        {"code": "Goppa 32,16", "baseline": 7, "phase1": 7, "phase2": 8,
         "improved_in_phase2": True,
         "reason": "seed-sweep 12,000 (6 примитивных полиномов GF(32) x "
                   "2000 seed): 55 уникальных rref-подкодов, все d=7; "
                   "Затем гиперплоскостной зонд: СЛАУ f·w=1 по всем 128 "
                   "вес-7 сообщениям parent РЕШИМА => ker f — 16-мерный "
                   "subcode без вес-7 слов, точный d=8 (A_8=400). "
                   "Интегрировано как derivation_method="
                   "'message_functional_kernel' (минимальное "
                   "обратимо-совместимое расширение from_parent; "
                   "алгоритм Goppa parent не менялся)"},
        {"code": "Wavelet 64,32", "baseline": "8 exact",
         "phase1": "11 <= d <= 14 (cert w=5)",
         "phase2": "без изменений (ТЗ §5: не трогать)",
         "improved_in_phase2": False},
    ],
    "searches": {
        "bch_phase2": {k: bch[k] for k in ("target","reached_target","seed",
            "evaluated_candidates","intermediate_checks","parent_configs",
            "elapsed_sec")},
        "rs_phase2": {k: rs[k] for k in ("target","reached_target","seed",
            "evaluations")},
        "goppa_phase2": {k: goppa[k] for k in ("target","reached_target",
            "budget_seeds_total","unique_codes","d_distribution",
            "elapsed_sec")},
        "goppa_hyperplane_probe": {
            "parents_probed": len(hyper),
            "solvable": sum(1 for r in hyper if r.get("solvable")),
            "best": [r for r in hyper if r.get("solvable")][0],
            "method": "exact: enumerate all weight-7 messages of parent "
                      "(full 2^17), solve f·w=1 over GF(2), enumerate "
                      "kernel subcode 2^16",
        },
    },
    "integration": {
        "changed_production": [
            "goppa/presets.py: GOPPA_32_16_* (seed=3, poly=59, "
            "subcode_functional, method message_functional_kernel)",
            "goppa/derived.py: from_parent(subcode_functional=None) — "
            "обратимо-совместимое расширение, default-путь побайтово "
            "старый (проверено fp 16/32-default/64)",
            "research/config.py: GOPPA_32_16_CONFIG (seed 3, poly 59, "
            "functional, d=8 8 8 + A_8 evidence), новое поле "
            "goppa_subcode_functional + JSON roundtrip, late FOUR_FAMILY "
            "override 7->8",
            "research/code_factory.py: сверка goppa_primitive_polynomial "
            "и goppa_subcode_functional конфиг<->пресет",
            "webapp backend: поле goppa_subcode_functional в схеме + "
            "fixture custom-preset обновлён",
            "tests/test_goppa_derived.py: bound-assert -> >= (смысл "
            "сохранён); tests/test_four_family_distance_metadata.py: "
            "[8,6,8,7]",
        ],
        "unchanged": "BCH-32 (6), RS-32 (7), все 16_8 и 64_32, wavelet-"
                     "32/64, LDPC — по ТЗ §2/§5 (не ухудшать, цели не "
                     "достигнуты — оставляем лучшие доказанные)",
    },
    "verification": verification,
    "reproduce_commands": [
        "python -m research.optimization.phase2.capture_phase2_baseline",
        "python -m research.optimization.phase2.verify_phase2",
        "python -m research.optimization.phase2.optimize_goppa_phase2 --seeds 2000",
        "python -m research.optimization.phase2.optimize_rs_phase2 --time-limit 2400 --chains 6 --seed 314001",
        "python -m research.optimization.phase2.optimize_bch_phase2 --time-limit 1500 --seed 222001",
    ],
}
out = p / "search_summary.json"
out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print("saved", out)
