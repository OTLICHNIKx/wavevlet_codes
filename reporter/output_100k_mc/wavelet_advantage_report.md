# Wavelet Code Advantage Report

Сформирован: 2026-10-01 22:17:48

> Сравнение производительности **Wavelet** кодов против конкурентов (BCH, Goppa, LDPC, Reed-Solomon) на различных каналах связи.

## Сводка

- **Источник данных**: bulk-файлов: 9; Monte Carlo файлов: 1
- **Эксперименты (bulk)**: rayleigh_16_8_100k, rayleigh_32_16_100k, rayleigh_64_32_100k, rayleigh_awgn_16_8_100k, rayleigh_awgn_32_16_100k, rayleigh_awgn_64_32_100k, sinusoidal_16_8_100k, sinusoidal_32_16_100k, sinusoidal_64_32_100k
- **Эксперименты (MC)**: mc:wavelet_channel_decoder_statistics_all_metrics
- **Всего точек сравнения**: 2160
- **Значимых побед Wavelet**: 479 (22.2%)
- **Ничьих (различие незначимо)**: 1306 (60.5%)
- **Значимых поражений**: 375 (17.4%)
- **Средний gain (конечный)**: 1.01x
- **Медиана gain**: 1.00x
- **Зон доминирования**: 17

> Победой считается только **статистически значимое** превосходство (z-score >= 2 по bulk-данным, непересечение 95% CI по MC) **и** относительный выигрыш BER не менее 2%. Различия ниже порога заносятся в ничьи.

---

# 1. Лучшие области преимущества Wavelet

## Канал: rayleigh

- rayleigh | 32/16 | chase | SNR 0.5 dB | средний gain 1.05x [rayleigh_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 2.5 dB | средний gain 1.05x [rayleigh_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 1.5 dB | средний gain 1.05x [rayleigh_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 3.5-4.5 dB | средний gain 1.05x [1 bulk, 1 MC] (против BCH, Goppa, LDPC, Reed-Solomon)

## Канал: rayleigh_awgn

- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 0.5 dB | средний gain 1.05x [rayleigh_awgn_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 1.5-2.5 dB | средний gain 1.05x [1 bulk, 1 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 3.5 dB | средний gain 1.03x [rayleigh_awgn_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 4.5 dB | средний gain 1.03x [rayleigh_awgn_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)

## Канал: sinusoidal

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 1.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 2.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 0.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 3.5 dB | средний gain 1.06x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 4.5 dB | средний gain 1.05x [sinusoidal_32_16_100k] (против BCH, Goppa, LDPC, Reed-Solomon)

---

# 2. Сравнение Wavelet против каждого семейства кодов

## Wavelet против BCH

Значимых побед: **162 / 540** (30.0%) | Ничьих/незначимых: 378 | Средний gain: 1.02x | Максимум: 1.24x | Медиана: 1.00x

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 32/16 | hard_mld | SNR 6 dB | средний gain 1.24x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | hard_mld | SNR 6 dB | средний gain 1.22x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.12x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | soft_mld | SNR 5 dB | средний gain 1.10x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 1.09x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.09x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.09x [1 bulk, 1 MC] (против BCH)
- rayleigh | 32/16 | chase | SNR 0-5 dB | средний gain 1.09x [1 bulk, 1 MC] (против BCH)
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.08x [1 bulk, 1 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 0-5 dB | средний gain 1.08x [1 bulk, 1 MC] (против BCH)
- sinusoidal | 32/16 | soft_mld | SNR 4 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.07x [1 bulk, 1 MC] (против BCH)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.06x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.06x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- rayleigh_awgn | 16/8 | soft_mld | SNR 5 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- rayleigh_awgn | 32/16 | soft_mld | SNR 5 dB | средний gain 1.05x [1 bulk, 1 MC] (против BCH)
- rayleigh | 32/16 | hard_mld | SNR 6 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- sinusoidal | 32/16 | soft_mld | SNR 3 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против BCH)
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.04x [1 bulk, 1 MC] (против BCH)

## Wavelet против Goppa

Значимых побед: **121 / 540** (22.4%) | Ничьих/незначимых: 419 | Средний gain: 1.00x | Максимум: 1.12x | Медиана: 1.00x

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 32/16 | hard_mld | SNR 6 dB | средний gain 1.12x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | hard_mld | SNR 6 dB | средний gain 1.10x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | soft_mld | SNR 5 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | soft_mld | SNR 4 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.05x [1 bulk, 1 MC] (против Goppa)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.04x [1 bulk, 1 MC] (против Goppa)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 16/8 | soft_mld | SNR 4-5 dB | средний gain 1.03x [sinusoidal_16_8_100k] (против Goppa)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh | 32/16 | hard_mld | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh_awgn | 32/16 | soft_mld | SNR 4-5 dB | средний gain 1.03x [1 bulk, 1 MC] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.03x [sinusoidal_32_16_100k] (против Goppa)
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.03x [1 bulk, 1 MC] (против Goppa)
- sinusoidal | 16/8 | soft_mld | SNR 2 dB | средний gain 1.02x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh | 32/16 | chase | SNR 0-5 dB | средний gain 1.02x [1 bulk, 1 MC] (против Goppa)
- sinusoidal | 16/8 | chase | SNR 2 dB | средний gain 1.02x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 1.02x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Goppa)

## Wavelet против LDPC

Значимых побед: **134 / 540** (24.8%) | Ничьих/незначимых: 406 | Средний gain: 1.01x | Максимум: 1.24x | Медиана: 1.00x

> Топ-20 зон значимого преимущества:

- rayleigh_awgn | 32/16 | hard_mld | SNR 6 dB | средний gain 1.24x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | hard_mld | SNR 6 dB | средний gain 1.21x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.13x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | soft_mld | SNR 5 dB | средний gain 1.12x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.09x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.09x [1 bulk, 1 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 0-5 dB | средний gain 1.08x [1 bulk, 1 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 1.08x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.08x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.08x [1 bulk, 1 MC] (против LDPC)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.08x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 0-5 dB | средний gain 1.08x [1 bulk, 1 MC] (против LDPC)
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.06x [1 bulk, 1 MC] (против LDPC)
- rayleigh | 32/16 | hard_mld | SNR 6 dB | средний gain 1.06x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | soft_mld | SNR 4 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 32/16 | soft_mld | SNR 3 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)
- sinusoidal | 16/8 | soft_mld | SNR 4.5-5 dB | средний gain 1.05x [sinusoidal_16_8_100k] (против LDPC)
- rayleigh_awgn | 32/16 | soft_mld | SNR 4-5 dB | средний gain 1.04x [1 bulk, 1 MC] (против LDPC)
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | средний gain 1.04x [1 bulk, 1 MC] (против LDPC)
- rayleigh_awgn | 16/8 | soft_mld | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против LDPC)

## Wavelet против Reed-Solomon

Значимых побед: **62 / 540** (11.5%) | Ничьих/незначимых: 478 | Средний gain: 1.00x | Максимум: 1.08x | Медиана: 1.00x

> Топ-20 зон значимого преимущества:

- sinusoidal | 32/16 | soft_mld | SNR 5 dB | средний gain 1.08x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.06x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 5 dB | средний gain 1.05x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 1.04x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 4 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 4 dB | средний gain 1.03x [mc:wavelet_channel_decoder_statistics_all_metrics] (против Reed-Solomon)
- rayleigh_awgn | 16/8 | chase | SNR 5 dB | средний gain 1.02x [rayleigh_awgn_16_8_100k] (против Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 0-5 dB | средний gain 1.01x [1 bulk, 1 MC] (против Reed-Solomon)
- rayleigh_awgn | 16/8 | chase | SNR 3.5 dB | средний gain 1.01x [rayleigh_awgn_16_8_100k] (против Reed-Solomon)
- sinusoidal | 16/8 | soft_mld | SNR 0-0.5 dB | средний gain 1.01x [sinusoidal_16_8_100k] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 0-3.5 dB | средний gain 1.01x [1 bulk, 1 MC] (против Reed-Solomon)
- sinusoidal | 16/8 | chase | SNR 0-0.5 dB | средний gain 1.01x [sinusoidal_16_8_100k] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 0-5 dB | средний gain 1.01x [1 bulk, 1 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 4.5-5 dB | средний gain 1.01x [rayleigh_awgn_32_16_100k] (против Reed-Solomon)
- rayleigh_awgn | 16/8 | hard_mld | SNR 1.5 dB | средний gain 1.01x [rayleigh_awgn_16_8_100k] (против Reed-Solomon)
- sinusoidal | 16/8 | syndrome | SNR 2.5 dB | средний gain 1.01x [sinusoidal_16_8_100k] (против Reed-Solomon)
- sinusoidal | 16/8 | syndrome | SNR 1 dB | средний gain 1.01x [sinusoidal_16_8_100k] (против Reed-Solomon)
- rayleigh_awgn | 16/8 | syndrome | SNR 0-1 dB | средний gain 1.00x [rayleigh_awgn_16_8_100k] (против Reed-Solomon)

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

Точек со **значимым** превосходством конкурента: **375**

- rayleigh | 32/16 | hard_mld | SNR 0-5 dB | уступает: Reed-Solomon
- rayleigh | 32/16 | soft_mld | SNR 0 dB | уступает: BCH
- rayleigh | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 64/32 | chase | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 64/32 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB | уступает: Reed-Solomon
- rayleigh_awgn | 32/16 | soft_mld | SNR 0-3.5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 64/32 | syndrome | SNR 0-5 dB | уступает: Goppa, LDPC, Reed-Solomon
- sinusoidal | 16/8 | syndrome | SNR 0 dB; 4.5-5 dB | уступает: BCH, LDPC, Reed-Solomon
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB | уступает: Reed-Solomon
- sinusoidal | 32/16 | soft_mld | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 64/32 | chase | SNR 0-5 dB | уступает: Goppa, LDPC, Reed-Solomon
- sinusoidal | 64/32 | syndrome | SNR 0-5 dB | уступает: Goppa, LDPC, Reed-Solomon

---

# 5. Таблица лидеров

| Channel | Code size | Decoder | SNR range | Gain | Experiment |
|---------|-----------|---------|-----------|------|------------|
| sinusoidal | 32/16 | chase | 6 dB | 1.07x | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| rayleigh_awgn | 32/16 | soft_mld | 6 dB | 1.07x | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| sinusoidal | 32/16 | soft_mld | 6 dB | 1.07x | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| sinusoidal | 32/16 | chase | 1.5 dB | 1.06x | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 2.5 dB | 1.06x | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 0.5 dB | 1.06x | [sinusoidal_32_16_100k] |
| sinusoidal | 32/16 | chase | 3.5 dB | 1.06x | [sinusoidal_32_16_100k] |
| rayleigh_awgn | 16/8 | chase | 6 dB | 1.05x | [mc:wavelet_channel_decoder_statistics_all_metrics] |
| sinusoidal | 32/16 | chase | 4.5 dB | 1.05x | [sinusoidal_32_16_100k] |
| rayleigh | 32/16 | chase | 0.5 dB | 1.05x | [rayleigh_32_16_100k] |
| rayleigh_awgn | 32/16 | chase | 0.5 dB | 1.05x | [rayleigh_awgn_32_16_100k] |
| rayleigh | 32/16 | chase | 2.5 dB | 1.05x | [rayleigh_32_16_100k] |
| rayleigh_awgn | 32/16 | chase | 1.5-2.5 dB | 1.05x | [1 bulk, 1 MC] |
| rayleigh | 32/16 | chase | 1.5 dB | 1.05x | [rayleigh_32_16_100k] |
| rayleigh | 32/16 | chase | 3.5-4.5 dB | 1.05x | [1 bulk, 1 MC] |
| rayleigh_awgn | 32/16 | chase | 3.5 dB | 1.03x | [rayleigh_awgn_32_16_100k] |
| rayleigh_awgn | 32/16 | chase | 4.5 dB | 1.03x | [rayleigh_awgn_32_16_100k] |

---

# 6. Итоговые выводы

- Wavelet показывает преимущество на канале sinusoidal при параметрах 32/16 (декодер chase) в диапазоне SNR 6 dB со средним выигрышем BER 1.07x [mc:wavelet_channel_decoder_statistics_all_metrics] против BCH, Goppa, LDPC, Reed-Solomon.
- Области доминирования зафиксированы против: BCH, Goppa, LDPC, Reed-Solomon.
- Наибольшее среднее преимущество относительно BCH: 1.02x (162/540 сравнений в пользу Wavelet).
- Области проигрыша: на канале rayleigh_awgn при 64/32 (декодер chase) в диапазоне SNR 6 dB Wavelet уступает части конкурентов.
