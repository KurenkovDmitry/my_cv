#pragma once

#include <optional>
#include <string>

namespace portfolio_cv_importer {

/**
 * Разжимает stream-часть PDF-объекта.
 */
std::optional<std::string> InflateObjectStream(const std::string& body_text);

}  // namespace portfolio_cv_importer
