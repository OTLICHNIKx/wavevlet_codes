import json
import pathlib

p = pathlib.Path("research_results/code_optimization")

baseline = json.loads((p / "baseline.json").read_text(encoding="utf-8"))
bch1 = json.loads((p / "bch_32_16_candidates.json").read_text(encoding="utf-8"))
bch2 = json.loads((p / "bch_32_16_phase2_candidates.json").read_text(encoding="utf-8"))
goppa = json.loads((p / "goppa_32_16_candidates.json").read_text(encoding="utf-8"))
rs1 = json.loads((p / "rs_32_16_candidates_phase2_withpoints.json").read_text(encoding="utf-8"))
rsp = json.loads((p / "rs_32_16_provenance.json").read_text(encoding="utf-8"))
wave_finalists = json.loads((p / "wavelet_64_32_finalists.json").read_text(encoding="utf-8"))
wave_best = json.loads((p / "wavelet_64_32_best.json").read_text(encoding="utf-8"))
verification = json.loads((p / "verification.json").read_text(encoding="utf-8"))


def base_entry(size, family):
    for entry in baseline[size]:
        if entry["family"] == family:
            return entry
    raise KeyError((size, family))


summary = {
    "task": "code_parameter_optimization (offline design stage)",
    "families": [
        {
            "family": "wavelet",
            "n": 64, "k": 32,
            "baseline": {
                "parameters": {"h_len": 32, "shift": 1},
                "distance_exact": None,
                "distance_lower_bound": 8,
                "distance_upper_bound": 8,
                "fingerprint": base_entry("64_32", "wavelet")["fingerprint_rref_G"],
                "note": "weight-8 codeword found by project scripts => exact 8",
            },
            "search": {
                "algorithm": "two-stage hill climbing on syndrome-certificate "
                             "violations (w=3 then w=4) over (h, shift), "
                             "a=b=1, g derived; deterministic per seed",
                "script": "research/optimization/optimize_wavelet_64_32.py",
                "seeds": [11, 555],
                "outcome": "first restart reached 0 violations in both "
                           "stages (2 evaluations, seed 11); second seed "
                           "555 produced an independent candidate (len 20)",
            },
            "best": {
                "parameters": wave_finalists["cand1_len16_shift5"]["parameters"],
                "distance_exact": None,
                "distance_lower_bound": 11,
                "distance_upper_bound": 14,
                "fingerprint": wave_finalists["cand1_len16_shift5"]["fingerprint"],
                "evidence": "strict syndrome certificate w=5 over all subsets "
                            "<=5 of H columns (no zero, pairwise distinct) => "
                            "no dependent sets <=10 => d>=11; a weight-14 "
                            "codeword found (exhaustive msg weight <=5 + "
                            "random) => d <= 14. Cross-checked by three "
                            "independent implementations (ldpc "
                            "minimum_distance_certificate, project "
                            "CompactSyndromeTable t=4: 679121/679121, no "
                            "collisions, direct S1..S5 enumeration in "
                            "finalize_wavelet_candidates.py)",
            },
            "integrated": True,
        },
        {
            "family": "bch_derived",
            "n": 32, "k": 16,
            "baseline": {
                "parameters": {
                    "m": 6, "designed_distance": 7, "shortening": 29,
                    "puncture": 2, "puncture_coordinates": "default (last 2)",
                },
                "distance_exact": 5,
                "fingerprint": base_entry("32_16", "bch_derived")["fingerprint_rref_G"],
            },
            "search": {
                "phase1": {
                    "algorithm": "exhaustive over all C(18,2)=153 parity "
                                 "puncture pairs, exact d by full 2^16 "
                                 "enumeration + weight enumerator",
                    "script": "research/optimization/optimize_bch_32_16.py",
                    "pairs": 153,
                    "result": "max d=6 at pairs (20,22) (A_6=14) and "
                              "(others, A_6>=14); all shortened [34,16] "
                              "codes have d=7 so d>=7 after puncture 2 is "
                              "impossible in this construction",
                },
                "phase2": {
                    "algorithm": "alternative valid parents per TZ 7.2: "
                                 "[63,39,>=9] p=8, [63,36,>=11] p=11, "
                                 "[63,30,>=9,root5] p=17; sampled "
                                 "shortening sets (new "
                                 "shortening_coordinates support added to "
                                 "bch/derived.py as minimal generalization, "
                                 "default behavior byte-identical) + "
                                 "puncture-set local search",
                    "script": "research/optimization/optimize_bch_32_16_phase2.py",
                    "seed": 7001,
                    "samples": 60,
                    "result": "max d=6 across all configurations tested; "
                              "d>=7 not found within budget",
                },
            },
            "best": {
                "parameters": {
                    "m": 6, "designed_distance": 7, "shortening": 29,
                    "puncture_coordinates": [20, 22],
                },
                "distance_exact": 6,
                "A_dmin": 14,
                "fingerprint": bch1["top"][0]["fingerprint"],
                "evidence": "exact 2^16 enumeration; tie-broken by A_dmin and A_{d+1} among all 153 pairs",
            },
            "integrated": True,
            "target_d_>=7_not_reached": "honest max in this family's "
                                        "search space at equal (n,k) is 6 "
                                        "for puncture 2 (structural: all "
                                        "[34,16] shortenings keep d=7)",
        },
        {
            "family": "goppa_derived",
            "n": 32, "k": 16,
            "baseline": {
                "parameters": {"m": 5, "degree": 3, "seed": 42},
                "distance_exact": 7,
                "A_dmin": base_entry("32_16", "goppa_derived")["distance_exact_enum"]["A_dmin"],
                "fingerprint": base_entry("32_16", "goppa_derived")["fingerprint_rref_G"],
            },
            "search": {
                "algorithm": "deterministic seed sweep x all 6 primitive "
                             "degree-5 polynomials; exact d per unique code",
                "script": "research/optimization/optimize_goppa_32_16.py",
                "seeds_per_polynomial": 1500,
                "unique_codes": goppa["search"]["unique_codes"],
                "d_distribution": {"7": 55},
                "result": "max d=7 (no candidate reached 8)",
            },
            "best": {
                "parameters": {"m": 5, "degree": 3, "seed": 3, "primitive_polynomial": 59},
                "distance_exact": 7,
                "A_dmin": 95,
                "fingerprint": goppa["top"][0]["fingerprint"],
                "evidence": "exact 2^16 enumeration",
            },
            "integrated": False,
            "decision": "baseline kept: A_7 improves 100 -> 95 only, not an "
                        "objectively better secondary criterion (TZ 8.3)",
        },
        {
            "family": "reed_solomon_binary",
            "n": 32, "k": 16,
            "baseline": {
                "parameters": {
                    "m": 4, "symbol_n": 8, "symbol_k": 4,
                    "primitive_polynomial": 19,
                    "evaluation_points": [0, 1, 2, 3, 4, 5, 6, 7],
                    "column_multipliers": [1, 1, 1, 1, 1, 1, 1, 1],
                },
                "distance_exact": 6,
                "A_dmin": base_entry("32_16", "reed_solomon_binary")["distance_exact_enum"]["A_dmin"],
                "fingerprint": base_entry("32_16", "reed_solomon_binary")["fingerprint_rref_G"],
            },
            "search": rsp,
            "best": {
                "parameters": {
                    "column_multipliers": [4, 6, 13, 7, 8, 12, 15, 10],
                    "evaluation_points": [0, 1, 2, 3, 4, 5, 6, 7],
                },
                "distance_exact": 7,
                "A_dmin": 28,
                "fingerprint": rsp["runs"][0]["best"]["fingerprint"],
                "evidence": "exact binary 2^16 enumeration of the production "
                            "config code (re-verified in verification.json)",
            },
            "integrated": True,
            "target_d_8_not_reached": "34244 exact evaluations (both phases) "
                                      "capped at d=7",
        },
        {
            "family": "ldpc + wavelet 32_16",
            "n": 32, "k": 16,
            "decision": "unchanged per TZ 10 (both exact d=8, reference "
                        "strong representatives)",
        },
    ],
    "verification": verification,
    "commands_to_reproduce_verification_only": [
        "python -m research.optimization.capture_baseline",
        "python -m research.optimization.verify_optimized_codes",
        "python -m research.optimization.finalize_wavelet_candidates",
    ],
    "integrated_changes": [
        "research/config.py: WAVELET_64_32_CONFIG (h+shift+metadata)",
        "research/config.py: FOUR_FAMILY_WAVELET_64_32_CONFIG late metadata override",
        "research/config.py: BCH_DERIVED_32_16_CONFIG puncture (20,22) + metadata",
        "research/config.py: FOUR_FAMILY_BCH_DERIVED_32_16_CONFIG metadata",
        "research/config.py: REED_SOLOMON_32_16_CONFIG multipliers + metadata",
        "research/config.py: REED_SOLOMON_32_16_EQUAL_CONFIG metadata",
        "bch/derived.py: shorten_systematic_generator_matrix_at + wiring "
        "(backward compatible; default byte-identical, verified by "
        "fingerprints in verification.json)",
        "tests/test_four_family_distance_metadata.py: updated to new values",
    ],
}
out = p / "search_summary.json"
out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print("saved", out)
