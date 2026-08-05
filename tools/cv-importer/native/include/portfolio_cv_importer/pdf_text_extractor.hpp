#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace portfolio_cv_importer {

/**
 * Извлекает текстовые строки из PDF-файла через ToUnicode-карты без OCR.
 */
std::vector<std::string> ExtractLinesFromPdfFile(const std::filesystem::path& pdf_path);

/**
 * Извлекает текстовые строки из PDF-байтов через ToUnicode-карты без OCR.
 */
std::vector<std::string> ExtractLinesFromPdfBytes(const std::vector<unsigned char>& pdf_bytes);

}  // namespace portfolio_cv_importer
