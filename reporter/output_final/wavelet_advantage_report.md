# Wavelet Code Advantage Report

Сформирован: 2026-10-03 11:59:45

> Сравнение производительности **Wavelet** кодов против конкурентов (BCH, Goppa, LDPC, Reed-Solomon) на различных каналах связи.

## Сводка

- **Источник данных**: bulk-файлов: 9; Monte Carlo файлов: 1
- **Эксперименты (bulk)**: rayleigh_16_8_100k, rayleigh_32_16_100k, rayleigh_64_32_100k, rayleigh_awgn_16_8_100k, rayleigh_awgn_32_16_100k, rayleigh_awgn_64_32_100k, sinusoidal_16_8_100k, sinusoidal_32_16_100k, sinusoidal_64_32_100k
- **Эксперименты (MC)**: mc:wavelet_channel_decoder_statistics_all_metrics
- **Всего точек сравнения**: 1920
- **Значимых побед Wavelet**: 746 (38.9%)
- **Ничьих (различие незначимо)**: 1075 (56.0%)
- **Значимых поражений**: 99 (5.2%)
- **Средний gain (конечный)**: 1.21x
- **Медиана gain**: 1.01x
- **Зон доминирования**: 0

> Победой считается только **статистически значимое** превосходство (z-score >= 2 по bulk-данным, непересечение 95% CI по MC) **и** относительный выигрыш BER не менее 2%. Различия ниже порога заносятся в ничьи.

> ⚠️ **Важно про честность:** из 746 значимых побед **539** получены при **разной ёмкости декодера** (у Wavelet syndrome t выше, чем у конкурента — например t=5 против t=4). Такие победы — следствие большего расстояния d_min (оно и позволяет поставить t больше), а не «волшебства» конструкции. Настоящее сравнение кодов — только **207** побед при **равном t**.

---

# 1. Лучшие области преимущества Wavelet

Нет точек, где Wavelet выигрывает у всех конкурентов одновременно.

---

# 2. Сравнение Wavelet против каждого семейства кодов

## Wavelet против BCH

Побед: **257** | Ничьих: 214 | Поражений: 9 | всего 480 (53.5% побед) | Средний gain: 1.31x | Медиана: 1.05x

    из побед **при равном t декодера**: 73; при разном t (артефакт ёмкости): 184; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 12 dB | средний gain 17.40x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 11 dB | средний gain 9.40x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 9.38x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 7.00x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 8 dB | средний gain 4.88x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 7 dB | средний gain 3.51x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 3.46x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.94x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 6 dB | средний gain 2.56x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 10 dB | средний gain 2.44x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 9 dB | средний gain 2.03x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 8 dB | средний gain 1.71x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 7 dB | средний gain 1.48x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | средний gain 1.37x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 6 dB | средний gain 1.31x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 12 dB | средний gain 1.26x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 9 dB | средний gain 1.26x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 11 dB | средний gain 1.26x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 10 dB | средний gain 1.26x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 8 dB | средний gain 1.25x [1 bulk, 1 MC] (против BCH)  ⚠️ разный t

## Wavelet против Goppa

Побед: **59** | Ничьих: 347 | Поражений: 74 | всего 480 (12.3% побед) | Средний gain: 0.99x | Медиана: 1.00x

    из побед **при равном t декодера**: 59; при разном t (артефакт ёмкости): 0; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 1.13x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.05x [rayleigh_awgn_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | soft_mld | SNR 5 dB | средний gain 1.04x [rayleigh_awgn_32_16_100k] (против Goppa)  ✓ равный t
- sinusoidal | 16/8 | soft_mld | SNR 4-5 dB | средний gain 1.03x [sinusoidal_16_8_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 1.03x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.03x [sinusoidal_32_16_100k] (против Goppa)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.03x [sinusoidal_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.03x [rayleigh_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 1.02x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 0-1.5 dB | средний gain 1.02x [rayleigh_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | chase | SNR 0 dB | средний gain 1.02x [rayleigh_awgn_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 1.02x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 16/8 | soft_mld | SNR 3.5 dB | средний gain 1.02x [rayleigh_awgn_16_8_100k] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 3.5 dB | средний gain 1.02x [rayleigh_32_16_100k] (против Goppa)  ✓ равный t

## Wavelet против LDPC

Побед: **258** | Ничьих: 218 | Поражений: 4 | всего 480 (53.8% побед) | Средний gain: 1.29x | Медиана: 1.04x

    из побед **при равном t декодера**: 74; при разном t (артефакт ёмкости): 184; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 12 dB | средний gain 14.52x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 8.85x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 11 dB | средний gain 8.55x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 6.78x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 8 dB | средний gain 4.86x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 7 dB | средний gain 3.48x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 3.45x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.93x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 6 dB | средний gain 2.55x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 10 dB | средний gain 2.44x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 9 dB | средний gain 2.03x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 8 dB | средний gain 1.71x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 7 dB | средний gain 1.48x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | средний gain 1.36x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 6 dB | средний gain 1.31x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 12 dB | средний gain 1.26x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 9 dB | средний gain 1.25x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 11 dB | средний gain 1.25x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 10 dB | средний gain 1.25x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 8 dB | средний gain 1.24x [1 bulk, 1 MC] (против LDPC)  ⚠️ разный t

## Wavelet против Reed-Solomon

Побед: **172** | Ничьих: 296 | Поражений: 12 | всего 480 (35.8% побед) | Средний gain: 1.27x | Медиана: 1.01x

    из побед **при равном t декодера**: 1; при разном t (артефакт ёмкости): 171; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 12 dB | средний gain 13.60x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 8.97x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 11 dB | средний gain 8.68x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 6.94x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 8 dB | средний gain 4.80x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 7 dB | средний gain 3.48x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 3.43x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.92x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 6 dB | средний gain 2.54x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 10 dB | средний gain 2.43x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 9 dB | средний gain 2.03x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 8 dB | средний gain 1.71x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 7 dB | средний gain 1.48x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | средний gain 1.36x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 6 dB | средний gain 1.30x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 12 dB | средний gain 1.26x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 11 dB | средний gain 1.25x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 9 dB | средний gain 1.25x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 10 dB | средний gain 1.25x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 8 dB | средний gain 1.24x [1 bulk, 1 MC] (против Reed-Solomon)  ⚠️ разный t

---

# 3. Равная ёмкость декодера (CI по сидам)

> Самый честный срез: Wavelet vs конкурент **при равном syndrome t**, вердикт по непересечению 95% CI 50 независимых сидов. Разный t (артефакт ёмкости) сюда не входит.

- rayleigh | 64/32 | chase | против Goppa: win=0 tie=2 loss=16 / 18 → **Goppa** лучше в 16/18
- rayleigh | 64/32 | syndrome | против Goppa: win=0 tie=18 loss=0 / 18 → паритет
- rayleigh_awgn | 64/32 | chase | против Goppa: win=0 tie=6 loss=12 / 18 → **Goppa** лучше в 12/18
- rayleigh_awgn | 64/32 | syndrome | против Goppa: win=0 tie=17 loss=1 / 18 → **Goppa** лучше в 1/18
- sinusoidal | 64/32 | chase | против Goppa: win=0 tie=16 loss=2 / 18 → **Goppa** лучше в 2/18
- sinusoidal | 64/32 | syndrome | против Goppa: win=0 tie=18 loss=0 / 18 → паритет

---

# 4. Подтверждение Monte Carlo

Подтверждённых MC-зон (совпали с bulk): **0**


Неподтверждённых/нестабильных MC-зон: **0**


---

# 5. Области, где Wavelet уступает конкурентам

Точек со **значимым** превосходством конкурента: **99**

- rayleigh | 64/32 | chase | SNR 0-5 dB; 6 dB; 7 dB; 8 dB; 9 dB; 10 dB; 11 dB; 12 dB | уступает: Goppa
- rayleigh_awgn | 32/16 | hard_mld | SNR 4-5 dB | уступает: Reed-Solomon
- rayleigh_awgn | 32/16 | soft_mld | SNR 0 dB; 1 dB | уступает: BCH
- rayleigh_awgn | 32/16 | syndrome | SNR 3.5-5 dB | уступает: BCH, LDPC
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB; 6 dB; 7 dB; 8 dB; 12 dB | уступает: Goppa
- sinusoidal | 16/8 | syndrome | SNR 5 dB | уступает: BCH
- sinusoidal | 32/16 | soft_mld | SNR 4.5-5 dB | уступает: BCH
- sinusoidal | 64/32 | chase | SNR 0-5 dB; 10 dB; 11 dB; 12 dB | уступает: Goppa, Reed-Solomon
- sinusoidal | 64/32 | syndrome | SNR 7 dB; 8 dB; 9 dB; 10 dB; 11 dB; 12 dB | уступает: Reed-Solomon

---

# 6. Таблица лидеров

Таблица пуста: нет зон доминирования.

---

# 7. Итоговые выводы

- Не обнаружено точек, где Wavelet выигрывает у всех конкурентов одновременно.
- Наибольшее среднее преимущество относительно BCH: 1.31x (257/480 сравнений в пользу Wavelet).
- Области проигрыша: на канале rayleigh_awgn при 64/32 (декодер chase) в диапазоне SNR 12 dB Wavelet уступает части конкурентов.
