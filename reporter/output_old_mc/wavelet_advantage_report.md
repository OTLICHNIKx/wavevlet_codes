# Wavelet Code Advantage Report

Сформирован: 2026-10-03 12:00:31

> Сравнение производительности **Wavelet** кодов против конкурентов (BCH, Goppa, LDPC, Reed-Solomon) на различных каналах связи.

## Сводка

- **Источник данных**: bulk-файлов: 9; Monte Carlo файлов: 1
- **Эксперименты (bulk)**: rayleigh_16_8_100k, rayleigh_32_16_100k, rayleigh_64_32_100k, rayleigh_awgn_16_8_100k, rayleigh_awgn_32_16_100k, rayleigh_awgn_64_32_100k, sinusoidal_16_8_100k, sinusoidal_32_16_100k, sinusoidal_64_32_100k
- **Эксперименты (MC)**: mc:wavelet_channel_decoder_statistics_all_metrics
- **Всего точек сравнения**: 2328
- **Значимых побед Wavelet**: 565 (24.3%)
- **Ничьих (различие незначимо)**: 1677 (72.0%)
- **Значимых поражений**: 86 (3.7%)
- **Средний gain (конечный)**: 1.09x
- **Медиана gain**: 1.00x
- **Зон доминирования**: 4

> Победой считается только **статистически значимое** превосходство (z-score >= 2 по bulk-данным, непересечение 95% CI по MC) **и** относительный выигрыш BER не менее 2%. Различия ниже порога заносятся в ничьи.

> ⚠️ **Важно про честность:** из 565 значимых побед **287** получены при **разной ёмкости декодера** (у Wavelet syndrome t выше, чем у конкурента — например t=5 против t=4). Такие победы — следствие большего расстояния d_min (оно и позволяет поставить t больше), а не «волшебства» конструкции. Настоящее сравнение кодов — только **278** побед при **равном t**.

---

# 1. Лучшие области преимущества Wavelet

## Канал: rayleigh_awgn

- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 8.58x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 5.69x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 2.88x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.48x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t

---

# 2. Сравнение Wavelet против каждого семейства кодов

## Wavelet против BCH

Побед: **201** | Ничьих: 372 | Поражений: 9 | всего 582 (34.5% побед) | Средний gain: 1.12x | Медиана: 1.00x

    из побед **при равном t декодера**: 101; при разном t (артефакт ёмкости): 100; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 11 dB | средний gain 11.62x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 11.22x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 12 dB | средний gain 7.80x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 7.33x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 8 dB | средний gain 4.86x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 3.54x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 7 dB | средний gain 3.50x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.98x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 6 dB | средний gain 2.57x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 10 dB | средний gain 2.44x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 9 dB | средний gain 2.03x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 8 dB | средний gain 1.73x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 7 dB | средний gain 1.49x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | средний gain 1.37x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 6 dB | средний gain 1.31x [rayleigh_awgn_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 12 dB | средний gain 1.27x [rayleigh_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 11 dB | средний gain 1.27x [rayleigh_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 9 dB | средний gain 1.25x [rayleigh_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 10 dB | средний gain 1.25x [rayleigh_64_32_100k] (против BCH)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 8 dB | средний gain 1.25x [rayleigh_64_32_100k] (против BCH)  ⚠️ разный t

## Wavelet против Goppa

Побед: **75** | Ничьих: 446 | Поражений: 61 | всего 582 (12.9% побед) | Средний gain: 1.00x | Медиана: 1.00x

    из побед **при равном t декодера**: 75; при разном t (артефакт ёмкости): 0; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 1.13x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | hard_mld | SNR 6 dB | средний gain 1.12x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.05x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | soft_mld | SNR 5 dB | средний gain 1.04x [rayleigh_awgn_32_16_100k] (против Goppa)  ✓ равный t
- sinusoidal | 16/8 | soft_mld | SNR 4-5 dB | средний gain 1.03x [sinusoidal_16_8_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 1.03x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.03x [sinusoidal_32_16_100k] (против Goppa)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.03x [sinusoidal_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.03x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | chase | SNR 0 dB | средний gain 1.03x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 0-1.5 dB | средний gain 1.02x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | chase | SNR 1 dB | средний gain 1.02x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)  ✓ равный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 1.02x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 1.02x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 16/8 | soft_mld | SNR 3.5 dB | средний gain 1.02x [rayleigh_awgn_16_8_100k] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 3.5 dB | средний gain 1.02x [rayleigh_32_16_100k] (против Goppa)  ✓ равный t

## Wavelet против LDPC

Побед: **201** | Ничьих: 377 | Поражений: 4 | всего 582 (34.5% побед) | Средний gain: 1.13x | Медиана: 1.00x

    из побед **при равном t декодера**: 101; при разном t (артефакт ёмкости): 100; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 11 dB | средний gain 11.66x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 11.06x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 12 dB | средний gain 10.03x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 7.15x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 8 dB | средний gain 4.79x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 3.50x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 7 dB | средний gain 3.46x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.98x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 6 dB | средний gain 2.56x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 10 dB | средний gain 2.46x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 9 dB | средний gain 2.03x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 8 dB | средний gain 1.73x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 7 dB | средний gain 1.49x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | средний gain 1.37x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 6 dB | средний gain 1.31x [rayleigh_awgn_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 12 dB | средний gain 1.26x [rayleigh_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 11 dB | средний gain 1.25x [rayleigh_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 8 dB | средний gain 1.25x [rayleigh_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 9 dB | средний gain 1.25x [rayleigh_64_32_100k] (против LDPC)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 10 dB | средний gain 1.24x [rayleigh_64_32_100k] (против LDPC)  ⚠️ разный t

## Wavelet против Reed-Solomon

Побед: **88** | Ничьих: 482 | Поражений: 12 | всего 582 (15.1% побед) | Средний gain: 1.11x | Медиана: 1.00x

    из побед **при равном t декодера**: 1; при разном t (артефакт ёмкости): 87; t неизвестен (MC-без-config): 0

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 11 dB | средний gain 11.67x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 10.91x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 12 dB | средний gain 10.20x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 7.25x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 8 dB | средний gain 4.71x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 3.47x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 7 dB | средний gain 3.46x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.94x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 6 dB | средний gain 2.55x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 10 dB | средний gain 2.43x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 9 dB | средний gain 2.03x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 8 dB | средний gain 1.72x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 7 dB | средний gain 1.49x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | средний gain 1.37x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 6 dB | средний gain 1.31x [rayleigh_awgn_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 12 dB | средний gain 1.27x [rayleigh_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 11 dB | средний gain 1.25x [rayleigh_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 9 dB | средний gain 1.25x [rayleigh_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 8 dB | средний gain 1.24x [rayleigh_64_32_100k] (против Reed-Solomon)  ⚠️ разный t
- rayleigh | 64/32 | chase | SNR 10 dB | средний gain 1.24x [rayleigh_64_32_100k] (против Reed-Solomon)  ⚠️ разный t

---

# 3. Равная ёмкость декодера (CI по сидам)

> Самый честный срез: Wavelet vs конкурент **при равном syndrome t**, вердикт по непересечению 95% CI 50 независимых сидов. Разный t (артефакт ёмкости) сюда не входит.

- rayleigh | 16/8 | chase | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | chase | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | chase | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | hard_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | hard_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | hard_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | hard_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | soft_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | soft_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | soft_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | soft_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 16/8 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | chase | против BCH: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh | 32/16 | chase | против Goppa: win=1 tie=6 loss=0 / 7 → **Wavelet** лучше в 1/7
- rayleigh | 32/16 | chase | против LDPC: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh | 32/16 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | hard_mld | против BCH: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh | 32/16 | hard_mld | против Goppa: win=6 tie=1 loss=0 / 7 → **Wavelet** лучше в 6/7
- rayleigh | 32/16 | hard_mld | против LDPC: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh | 32/16 | hard_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | soft_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | soft_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | soft_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | soft_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 32/16 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | chase | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | chase | против Goppa: win=0 tie=0 loss=7 / 7 → **Goppa** лучше в 7/7
- rayleigh | 64/32 | chase | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh | 64/32 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | chase | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | chase | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | chase | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | hard_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | hard_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | hard_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | hard_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | soft_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | soft_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | soft_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | soft_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 16/8 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | chase | против BCH: win=5 tie=2 loss=0 / 7 → **Wavelet** лучше в 5/7
- rayleigh_awgn | 32/16 | chase | против Goppa: win=2 tie=5 loss=0 / 7 → **Wavelet** лучше в 2/7
- rayleigh_awgn | 32/16 | chase | против LDPC: win=5 tie=2 loss=0 / 7 → **Wavelet** лучше в 5/7
- rayleigh_awgn | 32/16 | chase | против Reed-Solomon: win=1 tie=6 loss=0 / 7 → **Wavelet** лучше в 1/7
- rayleigh_awgn | 32/16 | hard_mld | против BCH: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh_awgn | 32/16 | hard_mld | против Goppa: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh_awgn | 32/16 | hard_mld | против LDPC: win=7 tie=0 loss=0 / 7 → **Wavelet** лучше в 7/7
- rayleigh_awgn | 32/16 | hard_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | soft_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | soft_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | soft_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | soft_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | syndrome | против BCH: win=0 tie=4 loss=3 / 7 → **BCH** лучше в 3/7
- rayleigh_awgn | 32/16 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 32/16 | syndrome | против LDPC: win=0 tie=5 loss=2 / 7 → **LDPC** лучше в 2/7
- rayleigh_awgn | 32/16 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 64/32 | chase | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 64/32 | chase | против Goppa: win=0 tie=0 loss=7 / 7 → **Goppa** лучше в 7/7
- rayleigh_awgn | 64/32 | chase | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 64/32 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 64/32 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 64/32 | syndrome | против Goppa: win=0 tie=3 loss=4 / 7 → **Goppa** лучше в 4/7
- rayleigh_awgn | 64/32 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- rayleigh_awgn | 64/32 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | chase | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | chase | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | chase | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | hard_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | hard_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | hard_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | hard_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | soft_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | soft_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | soft_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | soft_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 16/8 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | chase | против BCH: win=1 tie=6 loss=0 / 7 → **Wavelet** лучше в 1/7
- sinusoidal | 32/16 | chase | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | chase | против LDPC: win=1 tie=6 loss=0 / 7 → **Wavelet** лучше в 1/7
- sinusoidal | 32/16 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | hard_mld | против BCH: win=1 tie=6 loss=0 / 7 → **Wavelet** лучше в 1/7
- sinusoidal | 32/16 | hard_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | hard_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | hard_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | soft_mld | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | soft_mld | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | soft_mld | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | soft_mld | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | syndrome | против Goppa: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 32/16 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 64/32 | chase | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 64/32 | chase | против Goppa: win=0 tie=4 loss=3 / 7 → **Goppa** лучше в 3/7
- sinusoidal | 64/32 | chase | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 64/32 | chase | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 64/32 | syndrome | против BCH: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 64/32 | syndrome | против Goppa: win=0 tie=6 loss=1 / 7 → **Goppa** лучше в 1/7
- sinusoidal | 64/32 | syndrome | против LDPC: win=0 tie=7 loss=0 / 7 → паритет
- sinusoidal | 64/32 | syndrome | против Reed-Solomon: win=0 tie=7 loss=0 / 7 → паритет

---

# 4. Подтверждение Monte Carlo

Подтверждённых MC-зон (совпали с bulk): **0**


Неподтверждённых/нестабильных MC-зон: **0**


---

# 5. Области, где Wavelet уступает конкурентам

Точек со **значимым** превосходством конкурента: **86**

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

| Channel | Code size | Decoder | SNR range | Gain | t-честность | Experiment |
|---------|-----------|---------|-----------|------|-------------|------------|
| rayleigh_awgn | 64/32 | chase | 10 dB | 8.58x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| rayleigh_awgn | 64/32 | chase | 9 dB | 5.69x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| rayleigh_awgn | 64/32 | syndrome | 12 dB | 2.88x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| rayleigh_awgn | 64/32 | syndrome | 11 dB | 2.48x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |

---

# 7. Итоговые выводы

- Wavelet показывает преимущество на канале rayleigh_awgn при параметрах 64/32 (декодер chase) в диапазоне SNR 10 dB со средним выигрышем BER 8.58x [rayleigh_awgn_64_32_100k] против BCH, Goppa, LDPC, Reed-Solomon.
- Области доминирования зафиксированы против: BCH, Goppa, LDPC, Reed-Solomon.
- Наибольшее среднее преимущество относительно LDPC: 1.13x (201/582 сравнений в пользу Wavelet).
- Области проигрыша: на канале rayleigh_awgn при 64/32 (декодер chase) в диапазоне SNR 12 dB Wavelet уступает части конкурентов.
