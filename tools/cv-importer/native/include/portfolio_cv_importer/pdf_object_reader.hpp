#pragma once

#include <string>
#include <unordered_map>

namespace portfolio_cv_importer {

using PdfObjectMap = std::unordered_map<int, std::string>;

/**
 * Извлекает все объекты PDF как блоки latin1-текста.
 */
PdfObjectMap ParsePdfObjects(const std::string& pdf_text);

}  // namespace portfolio_cv_importer
