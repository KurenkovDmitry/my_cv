#include "portfolio_cv_importer/pdf_text_extractor.hpp"

#include "portfolio_cv_importer/pdf_object_reader.hpp"
#include "portfolio_cv_importer/pdf_stream_decoder.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace portfolio_cv_importer {

namespace {

struct TextItem {
  double x;
  double y;
  std::string text;
};

using UnicodeMap = std::unordered_map<std::string, std::string>;
using FontUnicodeMaps = std::unordered_map<int, UnicodeMap>;
using PageFontReferences = std::unordered_map<std::string, int>;

std::string Utf8FromCodePoint(int code_point) {
  std::string result;
  if (code_point <= 0x7F) {
    result.push_back(static_cast<char>(code_point));
    return result;
  }

  if (code_point <= 0x7FF) {
    result.push_back(static_cast<char>(0xC0 | ((code_point >> 6) & 0x1F)));
    result.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    return result;
  }

  if (code_point <= 0xFFFF) {
    result.push_back(static_cast<char>(0xE0 | ((code_point >> 12) & 0x0F)));
    result.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
    result.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    return result;
  }

  result.push_back(static_cast<char>(0xF0 | ((code_point >> 18) & 0x07)));
  result.push_back(static_cast<char>(0x80 | ((code_point >> 12) & 0x3F)));
  result.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
  result.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
  return result;
}

std::string UnicodeFromHex(const std::string& unicode_hex) {
  return Utf8FromCodePoint(std::stoi(unicode_hex, nullptr, 16));
}

std::string SourceCodeToKey(int source_code, std::size_t width) {
  std::ostringstream output_stream;
  output_stream << std::uppercase << std::hex << source_code;
  std::string key = output_stream.str();
  if (key.size() < width) {
    key.insert(0, width - key.size(), '0');
  }
  return key;
}

std::string NormalizeExtractedLine(const std::string& raw_line) {
  std::string normalized_line = raw_line;
  const std::pair<const char*, const char*> replacements[] = {
    {"Языкипрограммированияифреймворки", "Языки программирования и фреймворки"},
    {"Управлениепроектами", "Управление проектами"},
    {"Личныекачества", "Личные качества"},
    {"Сертификатыирекомендации", "Сертификаты и рекомендации"},
    {"УЧЕБНЫЕПРОЕКТЫ", "УЧЕБНЫЕ ПРОЕКТЫ"},
    {"Бауманскаяинженернаяшкола", "Бауманская инженерная школа"},
    {"Московскийгосударственныйтехническийуниверситет", "Московский государственный технический университет"},
    {"Производственнаяпрактика", "Производственная практика"},
    {"инженернойшколе", "инженерной школе"},
    {"поднагрузкой", "под нагрузкой"},
  };

  for (const auto& [source_fragment, target_fragment] : replacements) {
    const std::string source_string(source_fragment);
    const std::string target_string(target_fragment);
    std::size_t search_position = 0;
    while ((search_position = normalized_line.find(source_string, search_position)) != std::string::npos) {
      normalized_line.replace(search_position, source_string.size(), target_string);
      search_position += target_string.size();
    }
  }

  normalized_line = std::regex_replace(normalized_line, std::regex("\\s+"), " ");
  if (!normalized_line.empty() && normalized_line.front() == ' ') {
    normalized_line.erase(normalized_line.begin());
  }
  if (!normalized_line.empty() && normalized_line.back() == ' ') {
    normalized_line.pop_back();
  }
  return normalized_line;
}

UnicodeMap ParseToUnicodeMap(const std::string& unicode_stream) {
  UnicodeMap unicode_map;
  const std::regex block_pattern(R"((?:\d+)\s+begin(?:bfchar|bfrange)[\s\S]*?end(?:bfchar|bfrange))");
  const std::regex char_pattern(R"(^<([0-9A-F]+)>\s+<([0-9A-F]+)>$)", std::regex::icase);
  const std::regex range_pattern(R"(^<([0-9A-F]+)>\s+<([0-9A-F]+)>\s+<([0-9A-F]+)>$)", std::regex::icase);
  const std::regex array_pattern(R"(^<([0-9A-F]+)>\s+<([0-9A-F]+)>\s+\[(.+)\]$)", std::regex::icase);
  const std::regex array_target_pattern(R"(<([0-9A-F]+)>)", std::regex::icase);

  for (std::sregex_iterator block_iterator(unicode_stream.begin(), unicode_stream.end(), block_pattern), block_end;
       block_iterator != block_end;
       ++block_iterator) {
    std::istringstream block_stream((*block_iterator).str());
    std::string block_line;
    while (std::getline(block_stream, block_line)) {
      if (block_line.empty()) {
        continue;
      }

      std::smatch line_match;
      if (std::regex_match(block_line, line_match, char_pattern)) {
        unicode_map[line_match[1].str()] = UnicodeFromHex(line_match[2].str());
        continue;
      }

      if (std::regex_match(block_line, line_match, range_pattern)) {
        const int range_start = std::stoi(line_match[1].str(), nullptr, 16);
        const int range_end = std::stoi(line_match[2].str(), nullptr, 16);
        int target_code = std::stoi(line_match[3].str(), nullptr, 16);

        for (int source_code = range_start; source_code <= range_end; ++source_code, ++target_code) {
          unicode_map[SourceCodeToKey(source_code, line_match[1].str().size())] = UnicodeFromHex(
            SourceCodeToKey(target_code, 1)
          );
        }
        continue;
      }

      if (!std::regex_match(block_line, line_match, array_pattern)) {
        continue;
      }

      const int range_start = std::stoi(line_match[1].str(), nullptr, 16);
      int target_index = 0;
      for (std::sregex_iterator target_iterator(line_match[3].first, line_match[3].second, array_target_pattern), target_end;
           target_iterator != target_end;
           ++target_iterator, ++target_index) {
        unicode_map[SourceCodeToKey(range_start + target_index, line_match[1].str().size())] = UnicodeFromHex(
          (*target_iterator)[1].str()
        );
      }
    }
  }

  return unicode_map;
}

FontUnicodeMaps BuildFontToUnicodeMaps(const PdfObjectMap& pdf_objects) {
  FontUnicodeMaps font_maps;
  const std::regex to_unicode_pattern(R"(\/ToUnicode\s+(\d+)\s+0\s+R)");

  for (const auto& [object_id, body_text] : pdf_objects) {
    std::smatch to_unicode_match;
    if (!std::regex_search(body_text, to_unicode_match, to_unicode_pattern)) {
      continue;
    }

    const auto unicode_object_iterator = pdf_objects.find(std::stoi(to_unicode_match[1].str()));
    if (unicode_object_iterator == pdf_objects.end()) {
      continue;
    }

    const std::optional<std::string> unicode_stream = InflateObjectStream(unicode_object_iterator->second);
    if (!unicode_stream.has_value()) {
      continue;
    }

    font_maps[object_id] = ParseToUnicodeMap(unicode_stream.value());
  }

  return font_maps;
}

PageFontReferences ParsePageFontReferences(const std::string& body_text) {
  PageFontReferences font_references;
  const std::regex font_block_pattern(R"(\/Font\s*<<([\s\S]*?)>>)");
  const std::regex font_reference_pattern(R"(\/(F\d+)\s+(\d+)\s+0\s+R)");
  std::smatch font_block_match;

  if (!std::regex_search(body_text, font_block_match, font_block_pattern)) {
    return font_references;
  }

  for (std::sregex_iterator font_iterator(font_block_match[1].first, font_block_match[1].second, font_reference_pattern), font_end;
       font_iterator != font_end;
       ++font_iterator) {
    font_references[(*font_iterator)[1].str()] = std::stoi((*font_iterator)[2].str());
  }

  return font_references;
}

std::string DecodePdfLiteralText(const std::string& literal_text) {
  std::string decoded_text = literal_text;
  const std::pair<const char*, const char*> replacements[] = {
    {R"(\()", "("},
    {R"(\))", ")"},
    {R"(\n)", "\n"},
    {R"(\r)", "\r"},
    {R"(\t)", "\t"},
    {R"(\\)", R"(\)"},
  };

  for (const auto& [source_fragment, target_fragment] : replacements) {
    const std::string source_string(source_fragment);
    const std::string target_string(target_fragment);
    std::size_t search_position = 0;
    while ((search_position = decoded_text.find(source_string, search_position)) != std::string::npos) {
      decoded_text.replace(search_position, source_string.size(), target_string);
      search_position += target_string.size();
    }
  }

  return decoded_text;
}

std::string DecodePdfHexText(const std::string& hex_text, const UnicodeMap& unicode_map) {
  std::string decoded_text;
  for (std::size_t index = 0; index < hex_text.size(); index += 4) {
    const std::string glyph_chunk = hex_text.substr(index, std::min<std::size_t>(4, hex_text.size() - index));
    const auto glyph_iterator = unicode_map.find(glyph_chunk);
    if (glyph_iterator != unicode_map.end()) {
      decoded_text.append(glyph_iterator->second);
    }
  }
  return decoded_text;
}

std::string DecodePdfArrayText(const std::string& array_source, const UnicodeMap& unicode_map) {
  const std::regex token_pattern(R"(<([0-9A-F]+)>|\(((?:\\.|[^\\)])*)\)|(-?\d+(?:\.\d+)?))", std::regex::icase);
  std::string decoded_text;

  for (std::sregex_iterator token_iterator(array_source.begin(), array_source.end(), token_pattern), token_end;
       token_iterator != token_end;
       ++token_iterator) {
    if ((*token_iterator)[1].matched) {
      decoded_text.append(DecodePdfHexText((*token_iterator)[1].str(), unicode_map));
      continue;
    }

    if ((*token_iterator)[2].matched) {
      decoded_text.append(DecodePdfLiteralText((*token_iterator)[2].str()));
    }
  }

  return decoded_text;
}

std::vector<TextItem> ExtractTextItems(
  const std::string& content_stream,
  const PageFontReferences& page_font_references,
  const FontUnicodeMaps& font_to_unicode_maps
) {
  std::vector<TextItem> text_items;
  const std::regex font_pattern(R"(\/(F\d+)\s+[\d.]+\s+Tf)");
  const std::regex transform_pattern(R"(([\d.-]+)\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)\s+Tm)");
  const std::regex array_pattern(R"(\[(.*?)\]\s*TJ)");
  const std::regex literal_pattern(R"(\(((?:\\.|[^\\)])*)\)\s*Tj)");
  const std::regex hex_pattern(R"(<([0-9A-F]+)>\s*Tj)", std::regex::icase);

  std::string current_font_name;
  double current_text_x = 0.0;
  double current_text_y = 0.0;

  std::istringstream content_stream_reader(content_stream);
  std::string content_line;
  while (std::getline(content_stream_reader, content_line)) {
    std::smatch content_match;
    if (std::regex_search(content_line, content_match, font_pattern)) {
      current_font_name = content_match[1].str();
    }

    if (std::regex_search(content_line, content_match, transform_pattern)) {
      current_text_x = std::stod(content_match[2].str());
      current_text_y = std::stod(content_match[3].str());
    }

    UnicodeMap unicode_map;
    const auto font_reference_iterator = page_font_references.find(current_font_name);
    if (font_reference_iterator != page_font_references.end()) {
      const auto unicode_map_iterator = font_to_unicode_maps.find(font_reference_iterator->second);
      if (unicode_map_iterator != font_to_unicode_maps.end()) {
        unicode_map = unicode_map_iterator->second;
      }
    }

    for (std::sregex_iterator array_iterator(content_line.begin(), content_line.end(), array_pattern), array_end;
         array_iterator != array_end;
         ++array_iterator) {
      const std::string decoded_text = DecodePdfArrayText((*array_iterator)[1].str(), unicode_map);
      if (!decoded_text.empty()) {
        text_items.push_back({current_text_x, current_text_y, decoded_text});
      }
    }

    for (std::sregex_iterator literal_iterator(content_line.begin(), content_line.end(), literal_pattern), literal_end;
         literal_iterator != literal_end;
         ++literal_iterator) {
      const std::string decoded_text = DecodePdfLiteralText((*literal_iterator)[1].str());
      if (!decoded_text.empty()) {
        text_items.push_back({current_text_x, current_text_y, decoded_text});
      }
    }

    for (std::sregex_iterator hex_iterator(content_line.begin(), content_line.end(), hex_pattern), hex_end;
         hex_iterator != hex_end;
         ++hex_iterator) {
      const std::string decoded_text = DecodePdfHexText((*hex_iterator)[1].str(), unicode_map);
      if (!decoded_text.empty()) {
        text_items.push_back({current_text_x, current_text_y, decoded_text});
      }
    }
  }

  return text_items;
}

std::vector<std::string> GroupTextItemsIntoLines(const std::vector<TextItem>& text_items) {
  std::vector<TextItem> sorted_items = text_items;
  std::sort(
    sorted_items.begin(),
    sorted_items.end(),
    [](const TextItem& left_item, const TextItem& right_item) {
      if (left_item.y != right_item.y) {
        return left_item.y > right_item.y;
      }
      return left_item.x < right_item.x;
    }
  );

  struct GroupedLine {
    double y;
    std::vector<TextItem> items;
  };

  std::vector<GroupedLine> grouped_lines;
  for (const TextItem& text_item : sorted_items) {
    auto same_line_iterator = std::find_if(
      grouped_lines.begin(),
      grouped_lines.end(),
      [&text_item](const GroupedLine& grouped_line) {
        return std::fabs(grouped_line.y - text_item.y) < 2.5;
      }
    );

    if (same_line_iterator == grouped_lines.end()) {
      grouped_lines.push_back({text_item.y, {text_item}});
      continue;
    }

    same_line_iterator->items.push_back(text_item);
  }

  std::sort(
    grouped_lines.begin(),
    grouped_lines.end(),
    [](const GroupedLine& left_line, const GroupedLine& right_line) {
      return left_line.y > right_line.y;
    }
  );

  std::vector<std::string> result_lines;
  for (GroupedLine& grouped_line : grouped_lines) {
    std::sort(
      grouped_line.items.begin(),
      grouped_line.items.end(),
      [](const TextItem& left_item, const TextItem& right_item) {
        return left_item.x < right_item.x;
      }
    );

    std::string line_text;
    for (const TextItem& text_item : grouped_line.items) {
      line_text.append(text_item.text);
    }

    line_text = NormalizeExtractedLine(line_text);
    if (!line_text.empty()) {
      result_lines.push_back(line_text);
    }
  }

  return result_lines;
}

std::vector<unsigned char> ReadBinaryFile(const std::filesystem::path& pdf_path) {
  std::ifstream file_stream(pdf_path, std::ios::binary);
  if (!file_stream.is_open()) {
    throw std::runtime_error("Could not open PDF file for reading.");
  }

  return std::vector<unsigned char>(
    std::istreambuf_iterator<char>(file_stream),
    std::istreambuf_iterator<char>()
  );
}

}  // namespace

std::vector<std::string> ExtractLinesFromPdfFile(const std::filesystem::path& pdf_path) {
  return ExtractLinesFromPdfBytes(ReadBinaryFile(pdf_path));
}

std::vector<std::string> ExtractLinesFromPdfBytes(const std::vector<unsigned char>& pdf_bytes) {
  const std::string pdf_text(pdf_bytes.begin(), pdf_bytes.end());
  const PdfObjectMap pdf_objects = ParsePdfObjects(pdf_text);
  const FontUnicodeMaps font_to_unicode_maps = BuildFontToUnicodeMaps(pdf_objects);
  std::vector<std::string> page_lines;

  for (const auto& [object_id, body_text] : pdf_objects) {
    (void)object_id;
    if (body_text.find("/Type/Page") == std::string::npos) {
      continue;
    }

    const std::regex content_reference_pattern(R"(\/Contents\s+(\d+)\s+0\s+R)");
    std::smatch content_reference_match;
    if (!std::regex_search(body_text, content_reference_match, content_reference_pattern)) {
      continue;
    }

    const PageFontReferences page_font_references = ParsePageFontReferences(body_text);
    const auto content_object_iterator = pdf_objects.find(std::stoi(content_reference_match[1].str()));
    if (content_object_iterator == pdf_objects.end()) {
      continue;
    }

    const std::optional<std::string> content_stream = InflateObjectStream(content_object_iterator->second);
    if (!content_stream.has_value()) {
      continue;
    }

    const std::vector<TextItem> text_items = ExtractTextItems(
      content_stream.value(),
      page_font_references,
      font_to_unicode_maps
    );
    const std::vector<std::string> grouped_lines = GroupTextItemsIntoLines(text_items);
    page_lines.insert(page_lines.end(), grouped_lines.begin(), grouped_lines.end());
  }

  return page_lines;
}

}  // namespace portfolio_cv_importer
