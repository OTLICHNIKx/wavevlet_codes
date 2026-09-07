# Wavelet Codes

Исследовательский репозиторий Wavelet-, BCH-derived- и Goppa-derived-кодов.

Для настройки запусков и интерактивного просмотра `summary.csv` доступна локальная веб-оболочка: [webapp/README.md](webapp/README.md).

## Goppa-derived codes

Родительский бинарный Goppa-код `Γ(L, g)` строится над `GF(2^m)`. Полином
`g(x)` имеет коэффициенты из расширенного поля, является square-free и не
имеет корней на фиксированном support `L`. Элементы расширенной parity-check
matrix раскладываются по полиномиальному базису в бинарную матрицу `H`; базис
ядра `H` образует generator matrix `G`.

Для исследования зафиксированы конструкции `[16,8]`, `[32,16]` и `[64,32]`.
Родительские размерности равны соответственно `8`, `17` и `40`. Если parent
dimension больше целевой, из канонического RREF-базиса детерминированно
выбираются первые `k` строк, а для полученного подкода строится собственная
parity-check matrix. Поэтому общее название семейства — **Goppa-derived**;
`[16,8]` совпадает с родительским кодом, а `[32,16]` и `[64,32]` являются его
линейными подкодами.

Для square-free binary Goppa code степени `t` используется теоретическая
граница `d_min >= 2t + 1`. Она сохраняется и для подкода. Полным перебором
установлено точное `d_min=5` для `[16,8]` и `d_min=7` для `[32,16]`; для
`[64,32]` хранится только доказанная граница `d_min>=9`.

Пресет `EQUAL_DECODER_20K_THREE_FAMILIES` (и его smoke-версия
`EQUAL_DECODER_SMOKE_THREE_FAMILIES`) сравнивает Wavelet, BCH-derived и
Goppa-derived на одинаковых `(n,k)`, сообщениях, шуме BPSK/AWGN и decoder
budget. Используются общие Syndrome, Chase и MLD-декодеры проекта. Patterson
decoder в этот эксперимент не входит.

Это отдельные конфиги от исходного двухсемейного эксперимента
`EQUAL_DECODER_20K_CONFIG` / `EQUAL_DECODER_SMOKE_CONFIG` (Wavelet vs
BCH-derived, 6 кодов), который не изменялся и остаётся доступен как прежде.

## GRS binary и четыре семейства

Семейство `reed_solomon_binary` реализует binary image Generalized Reed–Solomon кода над `GF(2^m)` с явными `evaluation_points` и ненулевыми `column_multipliers`. Для целевого `[16,8]` используется `GRS(4,2)` над `GF(16)`, primitive polynomial `0b10011`, точки `(0,1,2,3)` и multipliers `(1,3,1,3)`. Полный перебор 255 ненулевых слов подтверждает `d_min=5`.

Четырёхсемейные presets сравнивают Wavelet, BCH-derived, Goppa-derived и GRS binary на одинаковых `(n,k,R)`, одинаковых сообщениях и base noise и с одинаковым decoder budget. Это **equal-(n,k,R) / equal-decoder** comparison; для `[32,16]` он намеренно не называется equal-distance, поскольку реальные exact distances составляют `8/5/7/6` соответственно. Для `[64,32]` общий syndrome radius установлен в `t=3`; metadata фиксирует Wavelet `d=8`, Goppa `d=9`, GRS `d=10` и BCH-derived `9 <= d <= 10` без ложного утверждения о равенстве расстояний.

В каждой строке `summary.csv` сохраняются `minimum_distance_exact`, `minimum_distance_lower_bound`, `minimum_distance_upper_bound` и `distance_evidence`.

Полные 20K-запуски выполняются командами:

```powershell
.\.venv\Scripts\python.exe -m research.run_compare_four_families_20k --size 16_8
.\.venv\Scripts\python.exe -m research.run_compare_four_families_20k --size 32_16
.\.venv\Scripts\python.exe -m research.run_compare_four_families_20k --size 64_32
```

После завершения результаты находятся в `research_results/four_families/`; каждый каталог содержит `summary.csv`.
