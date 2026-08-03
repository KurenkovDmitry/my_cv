#pragma once

#include <string>

namespace content_diff_native {

/**
 * Нормализованный результат сравнения двух документов.
 *
 * JSON возвращается строкой, чтобы Python bindings могли прозрачно отдать его как dict
 * после json.loads на Python-стороне.
 */
struct DiffResult {
  std::string summary_json;
};

/**
 * Сравнивает два сериализованных JSON-документа.
 *
 * C++ core специально остаётся компактным. SIMD/assembler добавляется только
 * после реального профилирования hot path.
 */
DiffResult compare_documents_json(const std::string& left_json, const std::string& right_json);

}  // namespace content_diff_native
