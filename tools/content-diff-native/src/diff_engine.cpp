#include "content_diff_native/diff_engine.hpp"

#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::vector<std::string> split_lines(const std::string& input) {
  std::vector<std::string> lines;
  std::stringstream stream(input);
  std::string line;

  while (std::getline(stream, line)) {
    if (!line.empty()) {
      lines.push_back(line);
    }
  }

  return lines;
}

std::string escape_json(const std::string& value) {
  std::string escaped;
  escaped.reserve(value.size() + 8);

  for (char current_char : value) {
    switch (current_char) {
      case '\\':
        escaped += "\\\\";
        break;
      case '"':
        escaped += "\\\"";
        break;
      case '\n':
        escaped += "\\n";
        break;
      case '\r':
        escaped += "\\r";
        break;
      case '\t':
        escaped += "\\t";
        break;
      default:
        escaped += current_char;
        break;
    }
  }

  return escaped;
}

}  // namespace

namespace content_diff_native {

DiffResult compare_documents_json(const std::string& left_json, const std::string& right_json) {
  const std::vector<std::string> left_lines = split_lines(left_json);
  const std::vector<std::string> right_lines = split_lines(right_json);

  std::map<std::string, std::string> left_lookup;
  std::map<std::string, std::string> right_lookup;
  std::set<std::string> changed_sections;

  for (std::size_t line_index = 0; line_index < left_lines.size(); ++line_index) {
    left_lookup[std::to_string(line_index)] = left_lines[line_index];
  }

  for (std::size_t line_index = 0; line_index < right_lines.size(); ++line_index) {
    right_lookup[std::to_string(line_index)] = right_lines[line_index];
  }

  std::vector<std::string> changed_paths;

  for (const auto& [line_key, left_value] : left_lookup) {
    const auto right_iterator = right_lookup.find(line_key);

    if (right_iterator == right_lookup.end() || right_iterator->second != left_value) {
      changed_paths.push_back("line:" + line_key);
      changed_sections.insert("content");
    }
  }

  for (const auto& [line_key, right_value] : right_lookup) {
    if (!left_lookup.contains(line_key)) {
      changed_paths.push_back("line:" + line_key);
      changed_sections.insert("content");
    }
  }

  std::ostringstream json_builder;
  json_builder << "{";
  json_builder << "\"summary\":{";
  json_builder << "\"changedPathsCount\":" << changed_paths.size() << ",";
  json_builder << "\"sectionsChangedCount\":" << changed_sections.size();
  json_builder << "},";

  json_builder << "\"changedPaths\":[";
  for (std::size_t index = 0; index < changed_paths.size(); ++index) {
    if (index > 0) {
      json_builder << ",";
    }
    json_builder << "\"" << escape_json(changed_paths[index]) << "\"";
  }
  json_builder << "],";

  json_builder << "\"sections\":[";
  std::size_t section_index = 0;
  for (const std::string& section_name : changed_sections) {
    if (section_index > 0) {
      json_builder << ",";
    }
    json_builder << "\"" << escape_json(section_name) << "\"";
    ++section_index;
  }
  json_builder << "]";
  json_builder << "}";

  return DiffResult{
      .summary_json = json_builder.str(),
  };
}

}  // namespace content_diff_native
