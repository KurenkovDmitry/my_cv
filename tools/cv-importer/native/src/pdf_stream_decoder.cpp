#include "portfolio_cv_importer/pdf_stream_decoder.hpp"

#include <vector>

#include <zlib.h>

namespace portfolio_cv_importer {

std::optional<std::string> InflateObjectStream(const std::string& body_text) {
  const std::size_t stream_index = body_text.find("stream");
  if (stream_index == std::string::npos) {
    return std::nullopt;
  }

  std::size_t stream_start_index = stream_index + 6;
  if (body_text.compare(stream_start_index, 2, "\r\n") == 0) {
    stream_start_index += 2;
  } else if (body_text.compare(stream_start_index, 1, "\n") == 0) {
    stream_start_index += 1;
  }

  const std::size_t stream_end_index = body_text.find("endstream", stream_start_index);
  if (stream_end_index == std::string::npos) {
    return std::nullopt;
  }

  std::size_t normalized_end_index = stream_end_index;
  if (normalized_end_index > 0 && body_text[normalized_end_index - 1] == '\n') {
    --normalized_end_index;
  }
  if (normalized_end_index > 0 && body_text[normalized_end_index - 1] == '\r') {
    --normalized_end_index;
  }

  const std::string compressed_bytes = body_text.substr(
    stream_start_index,
    normalized_end_index - stream_start_index
  );

  uLongf output_size = static_cast<uLongf>(compressed_bytes.size() * 4 + 1024);
  std::vector<unsigned char> output_buffer(output_size);

  int inflate_result = Z_BUF_ERROR;
  while (inflate_result == Z_BUF_ERROR) {
    inflate_result = uncompress(
      output_buffer.data(),
      &output_size,
      reinterpret_cast<const Bytef*>(compressed_bytes.data()),
      static_cast<uLong>(compressed_bytes.size())
    );

    if (inflate_result == Z_BUF_ERROR) {
      output_size *= 2;
      output_buffer.resize(output_size);
    }
  }

  if (inflate_result != Z_OK) {
    return std::nullopt;
  }

  return std::string(
    reinterpret_cast<const char*>(output_buffer.data()),
    static_cast<std::size_t>(output_size)
  );
}

}  // namespace portfolio_cv_importer
