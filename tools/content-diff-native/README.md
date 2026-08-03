# Content Diff Native

Нативная библиотека для сравнения:

- `current snapshot vs backup file`
- `backup file vs backup file`
- `import candidate vs draft/published`

## Цель

Библиотека существует для **on-demand diff**, а не для хранения diff в БД.

Это соответствует архитектурному решению:

- PostgreSQL хранит только текущее состояние;
- старые версии лежат в export/import bundle-файлах;
- diff строится по запросу из админки;
- тяжёлые сравнительные вычисления живут в native layer, а не в SQL.

## Слои

- `python/content_diff_native/`
  Python API для backend.
- `include/content_diff_native/`
  публичные C++ заголовки.
- `src/`
  C++ core.
- `python/bindings.cpp`
  pybind11 bindings.

## Почему пока без assembler

Assembler/SIMD здесь **не добавляется заранее**.

Правило остаётся таким:

1. сначала рабочий C++ core;
2. затем профилирование;
3. затем только в hot path можно изолированно добавить SIMD/assembler;
4. обязательно оставить безопасный fallback.

Это важно, потому что сервер небольшой, а сложность сопровождения low-level кода должна появляться только при подтверждённом bottleneck.

## Что уже заложено

- единый Python-вызов `compare_documents(left_payload, right_payload)`;
- нормализация JSON-подобных документов;
- summary diff;
- список изменённых путей;
- группировка по верхнеуровневым разделам.

## План развития

1. Подключить вызов из admin compare endpoints.
2. Добавить file-loader для export/import bundle.
3. Прогнать benchmark на реальных backup-файлах.
4. Только после benchmark решать, нужен ли SIMD/assembler для нормализации и hashing hot path.
