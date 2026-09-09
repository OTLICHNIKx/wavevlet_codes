"""Phase 2 офлайн-оптимизации (CODE_PARAMETER_OPTIMIZATION_PHASE2_TASK).

Новые измерения поиска:
  * BCH: короткие родительские коды с dd>=8/9, много shortening-наборов,
    полные puncture-переборы через быстрый учёт поддержек (без 2^16
    перебора на каждый puncture-кандидат);
  * RS: alternate field basis / column multipliers;
  * Goppa: расширенный seed-sweep.

Production-код не трогает этот пакет; интеграция — отдельный шаг
после строгой верификации.
"""
