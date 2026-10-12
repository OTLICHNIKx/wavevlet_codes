# Wavelet Code Advantage Report

Сформирован: 2026-10-02 11:09:35

> Сравнение производительности **Wavelet** кодов против конкурентов (BCH, Goppa, LDPC, Reed-Solomon) на различных каналах связи.

## Сводка

- **Источник данных**: bulk-файлов: 9; Monte Carlo файлов: 1
- **Эксперименты (bulk)**: rayleigh_16_8_100k, rayleigh_32_16_100k, rayleigh_64_32_100k, rayleigh_awgn_16_8_100k, rayleigh_awgn_32_16_100k, rayleigh_awgn_64_32_100k, sinusoidal_16_8_100k, sinusoidal_32_16_100k, sinusoidal_64_32_100k
- **Эксперименты (MC)**: mc:wavelet_channel_decoder_statistics_all_metrics
- **Всего точек сравнения**: 2328
- **Значимых побед Wavelet**: 761 (32.7%)
- **Ничьих (различие незначимо)**: 1264 (54.3%)
- **Значимых поражений**: 303 (13.0%)
- **Средний gain (конечный)**: 1.09x
- **Медиана gain**: 1.00x
- **Зон доминирования**: 21

> Победой считается только **статистически значимое** превосходство (z-score >= 2 по bulk-данным, непересечение 95% CI по MC) **и** относительный выигрыш BER не менее 2%. Различия ниже порога заносятся в ничьи.

> ⚠️ **Важно про честность:** из 761 значимых побед **312** получены при **разной ёмкости декодера** (у Wavelet syndrome t выше, чем у конкурента — например t=5 против t=4). Такие победы — следствие большего расстояния d_min (оно и позволяет поставить t больше), а не «волшебства» конструкции. Настоящее сравнение кодов — только **292** побед при **равном t**.

---

# 1. Лучшие области преимущества Wavelet

## Канал: rayleigh

- rayleigh | 32/16 | chase | SNR 0.5 dB | средний gain 1.05x [rayleigh_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 2.5 dB | средний gain 1.05x [rayleigh_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 1.5 dB | средний gain 1.05x [rayleigh_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- rayleigh | 32/16 | chase | SNR 3.5-4.5 dB | средний gain 1.05x [1 bulk, 1 MC] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t

## Канал: rayleigh_awgn

- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 8.58x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 5.69x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 12 dB | средний gain 2.88x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 2.48x [rayleigh_awgn_64_32_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ⚠️ разный t
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 0.5 dB | средний gain 1.05x [rayleigh_awgn_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- rayleigh_awgn | 32/16 | chase | SNR 1.5-2.5 dB | средний gain 1.05x [1 bulk, 1 MC] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- rayleigh_awgn | 32/16 | chase | SNR 3.5 dB | средний gain 1.03x [rayleigh_awgn_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- rayleigh_awgn | 32/16 | chase | SNR 4.5 dB | средний gain 1.03x [rayleigh_awgn_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t

## Канал: sinusoidal

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 1.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 2.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 0.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 3.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 4.5 dB | средний gain 1.05x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)  ✓ равный t

---

# 2. Сравнение Wavelet против каждого семейства кодов

## Wavelet против BCH

Значимых побед: **243 / 582** (41.8%) | Ничьих/незначимых: 339 | Средний gain: 1.12x | Максимум: 11.62x | Медиана: 1.00x

    из них **при равном t декодера**: 82; при разном t (артефакт ёмкости): 108; t неизвестен (MC): 53

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

Значимых побед: **125 / 582** (21.5%) | Ничьих/незначимых: 457 | Средний gain: 1.00x | Максимум: 1.13x | Медиана: 1.00x

    из них **при равном t декодера**: 86; при разном t (артефакт ёмкости): 0; t неизвестен (MC): 39

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 64/32 | chase | SNR 10 dB | средний gain 1.13x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | hard_mld | SNR 6 dB | средний gain 1.12x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | hard_mld | SNR 6 dB | средний gain 1.10x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | soft_mld | SNR 5 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | soft_mld | SNR 4 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.05x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.04x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 16/8 | soft_mld | SNR 4-5 dB | средний gain 1.03x [sinusoidal_16_8_100k] (против Goppa)  ✓ равный t
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh | 32/16 | hard_mld | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh_awgn | 64/32 | chase | SNR 9 dB | средний gain 1.03x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t
- rayleigh_awgn | 32/16 | soft_mld | SNR 4-5 dB | средний gain 1.03x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.03x [sinusoidal_32_16_100k] (против Goppa)  ✓ равный t
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.03x [1 bulk, 1 MC] (против Goppa)  ✓ равный t
- sinusoidal | 16/8 | soft_mld | SNR 2 dB | средний gain 1.02x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh_awgn | 64/32 | syndrome | SNR 11 dB | средний gain 1.02x [rayleigh_awgn_64_32_100k] (против Goppa)  ✓ равный t

## Wavelet против LDPC

Значимых побед: **241 / 582** (41.4%) | Ничьих/незначимых: 341 | Средний gain: 1.13x | Максимум: 11.66x | Медиана: 1.00x

    из них **при равном t декодера**: 80; при разном t (артефакт ёмкости): 108; t неизвестен (MC): 53

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

Значимых побед: **152 / 582** (26.1%) | Ничьих/незначимых: 430 | Средний gain: 1.11x | Максимум: 11.67x | Медиана: 1.00x

    из них **при равном t декодера**: 44; при разном t (артефакт ёмкости): 96; t неизвестен (MC): 12

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

# 3. Подтверждение Monte Carlo

Подтверждённых MC-зон (совпали с bulk): **4**

- rayleigh | 32/16 | chase | SNR 4 dB | средний gain 1.06x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 2 dB | средний gain 1.06x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 4 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 5 dB | средний gain 1.09x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)

Неподтверждённых/нестабильных MC-зон: **4**

- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)

---

# 4. Области, где Wavelet уступает конкурентам

Точек со **значимым** превосходством конкурента: **303**

- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | уступает: Reed-Solomon
- rayleigh | 32/16 | soft_mld | SNR 0 dB | уступает: BCH
- rayleigh | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 64/32 | chase | SNR 0-5 dB; 6 dB; 7 dB; 8 dB; 9 dB; 10 dB; 11 dB; 12 dB | уступает: Goppa
- rayleigh | 64/32 | syndrome | SNR 0-2 dB; 3-3.5 dB; 5 dB; 6 dB; 9 dB | уступает: Goppa
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | уступает: Reed-Solomon
- rayleigh_awgn | 32/16 | soft_mld | SNR 0-3.5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB; 6 dB; 7 dB; 8 dB; 12 dB | уступает: Goppa
- rayleigh_awgn | 64/32 | syndrome | SNR 0-5 dB; 6 dB; 7 dB | уступает: Goppa
- sinusoidal | 16/8 | syndrome | SNR 0 dB; 4.5-5 dB | уступает: BCH, LDPC, Reed-Solomon
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | уступает: Reed-Solomon
- sinusoidal | 32/16 | soft_mld | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 64/32 | chase | SNR 0-5 dB; 6 dB; 7 dB; 8 dB; 9 dB; 10 dB; 11 dB; 12 dB | уступает: Goppa, Reed-Solomon
- sinusoidal | 64/32 | syndrome | SNR 0-0.5 dB; 2 dB; 4 dB; 5 dB; 6 dB; 7 dB; 8 dB; 9 dB; 10 dB; 11 dB; 12 dB | уступает: Goppa, Reed-Solomon

---

# 5. Таблица лидеров

| Channel | Code size | Decoder | SNR range | Gain | t-честность | Experiment |
|---------|-----------|---------|-----------|------|-------------|------------|
| sinusoidal | 32/16 | chase | 1.5 dB | 1.06x | равный t | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 2.5 dB | 1.06x | равный t | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 0.5 dB | 1.06x | равный t | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 3.5 dB | 1.06x | равный t | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 4.5 dB | 1.05x | равный t | [sinusoidal_32_16_100k] |
| rayleigh | 32/16 | chase | 0.5 dB | 1.05x | равный t | [rayleigh_32_16_100k] |
| rayleigh_awgn | 32/16 | chase | 0.5 dB | 1.05x | равный t | [rayleigh_awgn_32_16_100k] |
| rayleigh | 32/16 | chase | 2.5 dB | 1.05x | равный t | [rayleigh_32_16_100k] |
| rayleigh_awgn | 32/16 | chase | 1.5-2.5 dB | 1.05x | равный t | [1 bulk, 1 MC] |
| rayleigh | 32/16 | chase | 1.5 dB | 1.05x | равный t | [rayleigh_32_16_100k] |
| rayleigh | 32/16 | chase | 3.5-4.5 dB | 1.05x | равный t | [1 bulk, 1 MC] |
| rayleigh_awgn | 32/16 | chase | 3.5 dB | 1.03x | равный t | [rayleigh_awgn_32_16_100k] |
| rayleigh_awgn | 32/16 | chase | 4.5 dB | 1.03x | равный t | [rayleigh_awgn_32_16_100k] |
| rayleigh_awgn | 64/32 | chase | 10 dB | 8.58x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| rayleigh_awgn | 64/32 | chase | 9 dB | 5.69x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| rayleigh_awgn | 64/32 | syndrome | 12 dB | 2.88x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| rayleigh_awgn | 64/32 | syndrome | 11 dB | 2.48x | разный t ⚠️ | [rayleigh_awgn_64_32_100k] |
| sinusoidal | 32/16 | chase | 6 dB | 1.07x | ? | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| rayleigh_awgn | 32/16 | soft_mld | 6 dB | 1.07x | ? | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| sinusoidal | 32/16 | soft_mld | 6 dB | 1.07x | ? | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| rayleigh_awgn | 16/8 | chase | 6 dB | 1.05x | ? | [mc:wavelet_channel_decoder_statistics_all_metrics] |

---

# 6. Итоговые выводы

- Wavelet показывает преимущество на канале rayleigh_awgn при параметрах 64/32 (декодер chase) в диапазоне SNR 10 dB со средним выигрышем BER 8.58x [rayleigh_awgn_64_32_100k] против BCH, Goppa, LDPC, Reed-Solomon.
- Области доминирования зафиксированы против: BCH, Goppa, LDPC, Reed-Solomon.
- Наибольшее среднее преимущество относительно LDPC: 1.13x (241/582 сравнений в пользу Wavelet).
- Области проигрыша: на канале rayleigh_awgn при 64/32 (декодер chase) в диапазоне SNR 12 dB Wavelet уступает части конкурентов.
