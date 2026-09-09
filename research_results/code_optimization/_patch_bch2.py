import pathlib

path = pathlib.Path('research/optimization/optimize_bch_32_16_phase2.py')
text = path.read_text(encoding='utf-8')

replacements = [
    (
        """        if d_sh - p < 7:
            continue  # потолок ниже цели — не тратим puncture-поиск""",
        """        if use_trivial_filter and d_sh - p < 7:
            continue  # потолок ниже цели — не тратим puncture-поиск""",
    ),
    (
        """        stall = 0
        while time.perf_counter() < deadline and stall < 400 and best_value < 9:""",
        """        stall = 0
        sample_deadline = min(deadline, time.perf_counter() + 4.0)
        while time.perf_counter() < sample_deadline and stall < 400 and best_value < 9:""",
    ),
    (
        '''    parser.add_argument("--samples", type=int, default=40)''',
        '''    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--trivial-filter", action="store_true")''',
    ),
    (
        """        all_results.extend(
            search_config(info, rng, deadline, args.samples)
        )""",
        """        all_results.extend(
            search_config(
                info,
                rng,
                deadline,
                args.samples,
                use_trivial_filter=args.trivial_filter,
            )
        )""",
    ),
]
for old, new in replacements:
    assert old in text, old[:50]
    text = text.replace(old, new)

path.write_text(text, encoding='utf-8')
import py_compile

py_compile.compile(str(path), doraise=True)
print('patched ok')
