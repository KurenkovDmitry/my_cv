#include "portfolio_cv_importer/pdf_object_reader.hpp"

#include <cstddef>

namespace portfolio_cv_importer {

PdfObjectMap ParsePdfObjects(const std::string& pdf_text) {
  PdfObjectMap pdf_objects;
  std::size_t cursor = 0;

  while (cursor < pdf_text.size()) {
    const std::size_t obj_pos = pdf_text.find(" obj", cursor);
    if (obj_pos == std::string::npos) {
      break;
    }

    const std::size_t line_start = pdf_text.rfind('\n', obj_pos);
    const std::size_t header_start = line_start == std::string::npos ? 0 : line_start + 1;
    const std::string header = pdf_text.substr(header_start, obj_pos - header_start);

    int object_id = 0;
    int generation_id = 0;
    if (std::sscanf(header.c_str(), "%d %d", &object_id, &generation_id) != 2) {
      cursor = obj_pos + 4;
      continue;
    }

    const std::size_t body_start = obj_pos + 4;
    const std::size_t body_end = pdf_text.find("endobj", body_start);
    if (body_end == std::string::npos) {
      break;
    }

    pdf_objects[object_id] = pdf_text.substr(body_start, body_end - body_start);
    cursor = body_end + 6;
  }

  return pdf_objects;
}

}  // namespace portfolio_cv_importer
