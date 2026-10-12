# Wavelet Code Advantage Report

Сформирован: 2026-09-27 00:18:28

> Сравнение производительности **Wavelet** кодов против конкурентов (BCH, Goppa, LDPC, Reed-Solomon) на различных каналах связи.

## Сводка

- **Источник данных**: bulk-файлов: 9; Monte Carlo файлов: 2
- **Эксперименты (bulk)**: rayleigh_16_8_20k, rayleigh_32_16_20k, rayleigh_64_32_20k, rayleigh_awgn_16_8_20k, rayleigh_awgn_32_16_20k, rayleigh_awgn_64_32_20k, sinusoidal_16_8_20k, sinusoidal_32_16_20k, sinusoidal_64_32_20k
- **Эксперименты (MC)**: mc:wavelet_channel_decoder_statistics, mc:wavelet_channel_decoder_statistics_all_metrics
- **Всего точек сравнения**: 3000
- **Побед Wavelet**: 914 (30.5%)
- **Средний выигрыш (конечный gain)**: 1.12x
- **Зон доминирования**: 16
- **Точек, где Wavelet уступает**: 2086

---

# 1. Лучшие области преимущества Wavelet

## Канал: rayleigh

- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 2.19x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 6 dB | средний gain 1.41x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 3 dB | средний gain 1.15x [1 bulk, 2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 4-4.5 dB | средний gain 1.12x [1 bulk, 2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 1.5 dB | средний gain 1.00x [rayleigh_32_16_20k] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 64/32 | syndrome | SNR 1.5 dB | средний gain 1.00x [rayleigh_64_32_20k] (против BCH, Goppa, LDPC, Reed-Solomon)

## Канал: rayleigh_awgn

- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 7.41x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.86x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 6 dB | средний gain 1.63x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 16/8 | syndrome | SNR 6 dB | средний gain 1.62x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 64/32 | syndrome | SNR 5 dB | средний gain 1.02x [1 bulk, 2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 64/32 | syndrome | SNR 1.5 dB | средний gain 1.00x [rayleigh_awgn_64_32_20k] (против BCH, Goppa, LDPC, Reed-Solomon)

## Канал: sinusoidal

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 22.81x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 6 dB | средний gain 2.34x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 5 dB | средний gain 1.65x [1 bulk, 2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 2-3.5 dB | средний gain 1.24x [1 bulk, 2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)

---

# 2. Сравнение Wavelet против каждого семейства кодов

## Wavelet против BCH

Побед: **206 / 750** (27.5%) | Средний gain: 1.14x | Максимум: 32.75x | Медиана: 0.91x

> Топ-20 точек преимущества:

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 32.75x [2 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 10.95x [2 MC] (против BCH)
- sinusoidal | 32/16 | chase | SNR 5 dB | средний gain 9.68x [2 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 5 dB | средний gain 6.93x [2 MC] (против BCH)
- sinusoidal | 32/16 | chase | SNR 4 dB | средний gain 6.63x [2 MC] (против BCH)
- sinusoidal | 32/16 | chase | SNR 3 dB | средний gain 4.77x [2 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 4 dB | средний gain 4.47x [2 MC] (против BCH)
- sinusoidal | 32/16 | chase | SNR 2 dB | средний gain 4.07x [2 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 3 dB | средний gain 3.28x [2 MC] (против BCH)
- sinusoidal | 32/16 | chase | SNR 1 dB | средний gain 3.06x [2 MC] (против BCH)
- sinusoidal | 32/16 | chase | SNR 0 dB | средний gain 2.79x [2 MC] (против BCH)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 2.75x [2 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 2 dB | средний gain 2.57x [2 MC] (против BCH)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 2.42x [2 MC] (против BCH)
- rayleigh_awgn | 32/16 | chase | SNR 1 dB | средний gain 2.38x [2 MC] (против BCH)
- rayleigh | 32/16 | chase | SNR 4 dB | средний gain 2.33x [2 MC] (против BCH)
- rayleigh | 32/16 | chase | SNR 5 dB | средний gain 2.31x [2 MC] (против BCH)
- rayleigh | 32/16 | chase | SNR 2 dB | средний gain 2.25x [2 MC] (против BCH)
- sinusoidal | 32/16 | syndrome | SNR 6 dB | средний gain 2.22x [2 MC] (против BCH)
- rayleigh | 32/16 | chase | SNR 3 dB | средний gain 2.18x [2 MC] (против BCH)

## Wavelet против Goppa

Побед: **230 / 750** (30.7%) | Средний gain: 1.16x | Максимум: 21.75x | Медиана: 0.94x

> Топ-20 точек преимущества:

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 21.75x [2 MC] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 5 dB | средний gain 6.40x [2 MC] (против Goppa)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 5.62x [2 MC] (против Goppa)
- rayleigh_awgn | 32/16 | chase | SNR 5 dB | средний gain 4.72x [2 MC] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 4 dB | средний gain 4.60x [2 MC] (против Goppa)
- sinusoidal | 16/8 | syndrome | SNR 6 dB | средний gain 3.87x [2 MC] (против Goppa)
- sinusoidal | 16/8 | syndrome | SNR 5 dB | средний gain 3.69x [2 MC] (против Goppa)
- sinusoidal | 16/8 | chase | SNR 6 dB | средний gain 3.43x [2 MC] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 2 dB | средний gain 3.29x [2 MC] (против Goppa)
- rayleigh_awgn | 16/8 | syndrome | SNR 6 dB | средний gain 3.28x [2 MC] (против Goppa)
- rayleigh_awgn | 32/16 | chase | SNR 4 dB | средний gain 3.28x [2 MC] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 3 dB | средний gain 3.14x [2 MC] (против Goppa)
- rayleigh_awgn | 16/8 | chase | SNR 6 dB | средний gain 3.14x [2 MC] (против Goppa)
- sinusoidal | 16/8 | syndrome | SNR 4 dB | средний gain 2.99x [2 MC] (против Goppa)
- rayleigh_awgn | 16/8 | syndrome | SNR 5 dB | средний gain 2.73x [2 MC] (против Goppa)
- rayleigh_awgn | 16/8 | chase | SNR 5 dB | средний gain 2.69x [2 MC] (против Goppa)
- sinusoidal | 16/8 | syndrome | SNR 3 dB | средний gain 2.60x [2 MC] (против Goppa)
- rayleigh_awgn | 32/16 | chase | SNR 3 dB | средний gain 2.57x [2 MC] (против Goppa)
- sinusoidal | 16/8 | chase | SNR 5 dB | средний gain 2.57x [2 MC] (против Goppa)
- sinusoidal | 32/16 | chase | SNR 1 dB | средний gain 2.54x [2 MC] (против Goppa)

## Wavelet против LDPC

Побед: **187 / 750** (24.9%) | Средний gain: 1.00x | Максимум: 11.75x | Медиана: 0.89x

> Топ-20 точек преимущества:

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 11.75x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 6.50x [2 MC] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 5 dB | средний gain 5.13x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 5 dB | средний gain 4.66x [2 MC] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 4 dB | средний gain 3.62x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 4 dB | средний gain 3.20x [2 MC] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 3 dB | средний gain 3.10x [2 MC] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 2 dB | средний gain 2.79x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 3 dB | средний gain 2.43x [2 MC] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 1 dB | средний gain 2.34x [2 MC] (против LDPC)
- sinusoidal | 32/16 | syndrome | SNR 6 dB | средний gain 2.28x [2 MC] (против LDPC)
- sinusoidal | 32/16 | chase | SNR 0 dB | средний gain 2.15x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 2 dB | средний gain 2.03x [2 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 5 dB | средний gain 1.99x [2 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 1.96x [2 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 4 dB | средний gain 1.96x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | chase | SNR 1 dB | средний gain 1.91x [2 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 2 dB | средний gain 1.87x [2 MC] (против LDPC)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.86x [2 MC] (против LDPC)
- rayleigh | 32/16 | chase | SNR 0 dB | средний gain 1.82x [2 MC] (против LDPC)

## Wavelet против Reed-Solomon

Побед: **291 / 750** (38.8%) | Средний gain: 1.20x | Максимум: 25.00x | Медиана: 0.99x

> Топ-20 точек преимущества:

- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 25.00x [2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 6.57x [2 MC] (против Reed-Solomon)
- sinusoidal | 32/16 | soft_mld | SNR 6 dB | средний gain 5.12x [2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 5 dB | средний gain 4.49x [2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 4 dB | средний gain 3.54x [2 MC] (против Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 2-5 dB | средний gain 2.99x [1 bulk, 2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 3 dB | средний gain 2.85x [2 MC] (против Reed-Solomon)
- sinusoidal | 64/32 | chase | SNR 6 dB | средний gain 2.48x [2 MC] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 2.44x [2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 2 dB | средний gain 2.37x [2 MC] (против Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 6 dB | средний gain 2.31x [2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 1 dB | средний gain 2.20x [2 MC] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 5 dB | средний gain 2.19x [2 MC] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 4 dB | средний gain 2.16x [2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 2.14x [2 MC] (против Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 0-1 dB | средний gain 2.00x [1 bulk, 2 MC] (против Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 0 dB | средний gain 2.00x [2 MC] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 2 dB | средний gain 2.00x [2 MC] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 3 dB | средний gain 1.97x [2 MC] (против Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 1 dB | средний gain 1.95x [2 MC] (против Reed-Solomon)

---

# 3. Подтверждение Monte Carlo

Подтверждённых MC-зон (совпали с bulk): **40**

- rayleigh_awgn | 32/16 | syndrome | SNR 0 dB | средний gain 1.09x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 1 dB | средний gain 1.11x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 2 dB | средний gain 1.15x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 3 dB | средний gain 1.23x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 4 dB | средний gain 1.31x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 5 dB | средний gain 1.45x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 0 dB | средний gain 1.88x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 1 dB | средний gain 2.09x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 2 dB | средний gain 2.26x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 3 dB | средний gain 2.78x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 4 dB | средний gain 3.62x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 5 dB | средний gain 5.20x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 1 dB | средний gain 1.16x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 2 dB | средний gain 1.19x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 3 dB | средний gain 1.23x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 4 dB | средний gain 1.23x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 5 dB | средний gain 1.35x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 1 dB | средний gain 1.90x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 2 dB | средний gain 2.02x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 3 dB | средний gain 1.97x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 4 dB | средний gain 2.11x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 5 dB | средний gain 2.09x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 0 dB | средний gain 1.13x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 1 dB | средний gain 1.21x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 2 dB | средний gain 1.36x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 3 dB | средний gain 1.56x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 4 dB | средний gain 1.71x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 5 dB | средний gain 1.97x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 0 dB | средний gain 2.48x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 1 dB | средний gain 2.70x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 2 dB | средний gain 3.39x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 3 dB | средний gain 3.73x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 4 dB | средний gain 4.72x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 5 dB | средний gain 6.92x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 64/32 | syndrome | SNR 3 dB | средний gain 1.01x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 64/32 | syndrome | SNR 4 dB | средний gain 1.02x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 64/32 | syndrome | SNR 5 dB | средний gain 1.03x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 64/32 | syndrome | SNR 4 dB | средний gain 1.05x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 64/32 | chase | SNR 0 dB | средний gain 1.04x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 64/32 | chase | SNR 2 dB | средний gain 1.07x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)

Неподтверждённых/нестабильных MC-зон: **10**

- rayleigh_awgn | 16/8 | syndrome | SNR 6 dB | средний gain 1.62x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | syndrome | SNR 6 dB | средний gain 1.63x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | chase | SNR 6 dB | средний gain 7.41x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh_awgn | 32/16 | soft_mld | SNR 6 dB | средний gain 1.86x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 0 dB | средний gain 1.14x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | syndrome | SNR 6 dB | средний gain 1.41x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 0 dB | средний gain 1.89x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- rayleigh | 32/16 | chase | SNR 6 dB | средний gain 2.19x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | syndrome | SNR 6 dB | средний gain 2.34x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)
- sinusoidal | 32/16 | chase | SNR 6 dB | средний gain 22.81x [2 MC] (против BCH, Goppa, LDPC, Reed-Solomon)

---

# 4. Области, где Wavelet уступает конкурентам

Точек, где Wavelet хуже хотя бы одного конкурента: **2086**

- rayleigh | 16/8 | chase | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 16/8 | hard_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 16/8 | soft_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 16/8 | syndrome | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 32/16 | chase | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 32/16 | hard_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 32/16 | soft_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 32/16 | syndrome | SNR 0-1 dB; 2-2.5 dB; 3.5 dB; 5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 64/32 | chase | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh | 64/32 | syndrome | SNR 0-1 dB; 2-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 16/8 | chase | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 16/8 | hard_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 16/8 | soft_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 16/8 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | chase | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | hard_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | soft_mld | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 32/16 | syndrome | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 64/32 | chase | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- rayleigh_awgn | 64/32 | syndrome | SNR 0-1 dB; 2-4.5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 16/8 | chase | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 16/8 | hard_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 16/8 | soft_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 16/8 | syndrome | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 32/16 | chase | SNR 0-5 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 32/16 | hard_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 32/16 | soft_mld | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 32/16 | syndrome | SNR 0-1.5 dB; 4-4.5 dB | уступает: BCH, LDPC
- sinusoidal | 64/32 | chase | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon
- sinusoidal | 64/32 | syndrome | SNR 0-5 dB; 6 dB | уступает: BCH, Goppa, LDPC, Reed-Solomon

---

# 5. Таблица лидеров

| Channel | Code size | Decoder | SNR range | Gain | Experiment |
|---------|-----------|---------|-----------|------|------------|
| sinusoidal | 32/16 | chase | 6 dB | 22.81x | [2 MC] |
| rayleigh_awgn | 32/16 | chase | 6 dB | 7.41x | [2 MC] |
| sinusoidal | 32/16 | syndrome | 6 dB | 2.34x | [2 MC] |
| rayleigh | 32/16 | chase | 6 dB | 2.19x | [2 MC] |
| rayleigh_awgn | 32/16 | soft_mld | 6 dB | 1.86x | [2 MC] |
| sinusoidal | 32/16 | syndrome | 5 dB | 1.65x | [1 bulk, 2 MC] |
| rayleigh_awgn | 32/16 | syndrome | 6 dB | 1.63x | [2 MC] |
| rayleigh_awgn | 16/8 | syndrome | 6 dB | 1.62x | [2 MC] |
| rayleigh | 32/16 | syndrome | 6 dB | 1.41x | [2 MC] |
| sinusoidal | 32/16 | syndrome | 2-3.5 dB | 1.24x | [1 bulk, 2 MC] |
| rayleigh | 32/16 | syndrome | 3 dB | 1.15x | [1 bulk, 2 MC] |
| rayleigh | 32/16 | syndrome | 4-4.5 dB | 1.12x | [1 bulk, 2 MC] |
| rayleigh_awgn | 64/32 | syndrome | 5 dB | 1.02x | [1 bulk, 2 MC] |
| rayleigh | 32/16 | syndrome | 1.5 dB | 1.00x | [rayleigh_32_16_20k] |
| rayleigh | 64/32 | syndrome | 1.5 dB | 1.00x | [rayleigh_64_32_20k] |
| rayleigh_awgn | 64/32 | syndrome | 1.5 dB | 1.00x | [rayleigh_awgn_64_32_20k] |

---

# 6. Итоговые выводы

- Wavelet показывает преимущество на канале sinusoidal при параметрах 32/16 (декодер chase) в диапазоне SNR 6 dB со средним выигрышем BER 22.81x [2 MC] против BCH, Goppa, LDPC, Reed-Solomon.
- Области доминирования зафиксированы против: BCH, Goppa, LDPC, Reed-Solomon.
- Наибольшее среднее преимущество относительно Reed-Solomon: 1.20x (291/750 сравнений в пользу Wavelet).
- Области проигрыша: на канале sinusoidal при 32/16 (декодер soft_mld) в диапазоне SNR 6 dB Wavelet уступает части конкурентов.
