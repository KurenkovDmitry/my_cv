#pragma once

#include <filesystem>
#include <string>
#include <unordered_map>
#include <vector>

namespace portfolio_cv_importer {

/**
 * Результат независимого от шаблона структурного разбора CV.
 */
struct ResumeLayout {
  std::string family;
  std::vector<std::string> header_lines;
  std::unordered_map<std::string, std::vector<std::string>> sections;
};

/**
 * Распознаёт распространённые русские и английские секции CV.
 */
ResumeLayout ParseResumeLayout(const std::vector<std::string>& extracted_lines);

/**
 * Выполняет полный нативный pipeline: PDF, строки, семантические секции.
 */
ResumeLayout ParseResumeLayoutFromPdfFile(const std::filesystem::path& pdf_path);

}  // namespace portfolio_cv_importer
