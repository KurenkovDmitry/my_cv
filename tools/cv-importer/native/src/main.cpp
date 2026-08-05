#include "portfolio_cv_importer/pdf_text_extractor.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
  if (argc < 2 || argc > 3) {
    std::cerr << "Usage: portfolio_cv_pdf_extract <source-pdf> [target-text]" << std::endl;
    return 1;
  }

  const std::filesystem::path source_path(argv[1]);
  const std::vector<std::string> extracted_lines = portfolio_cv_importer::ExtractLinesFromPdfFile(source_path);

  if (argc == 3) {
    std::ofstream output_stream(argv[2], std::ios::binary);
    for (const std::string& line : extracted_lines) {
      output_stream << line << '\n';
    }
    return 0;
  }

  for (const std::string& line : extracted_lines) {
    std::cout << line << '\n';
  }
  return 0;
}
