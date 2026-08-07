#include "portfolio_cv_importer/resume_layout_parser.hpp"

#include "portfolio_cv_importer/pdf_text_extractor.hpp"

#include <algorithm>
#include <cctype>
#include <optional>
#include <regex>
#include <unordered_map>

namespace portfolio_cv_importer {

namespace {

using HeadingAliases = std::unordered_map<std::string, std::vector<std::string>>;

const HeadingAliases kHeadingAliases = {
  {"summary", {"about", "about me", "profile", "professional summary", "summary", "обо мне", "о себе", "профиль"}},
  {"experience", {"career history", "employment history", "experience", "professional experience", "work experience", "карьера", "опыт", "опыт работы", "трудовая деятельность"}},
  {"education", {"academic background", "education", "education and training", "qualifications", "образование", "основное и дополнительное образование"}},
  {"skills", {"competencies", "core competencies", "expertise", "key skills", "skills", "technical skills", "компетенции", "ключевые навыки", "навыки", "стек", "технологии"}},
  {"projects", {"academic projects", "personal projects", "portfolio", "projects", "selected projects", "study projects", "портфолио", "проекты", "учебные проекты"}},
  {"certifications", {"awards", "certificates", "certifications", "licenses and certifications", "достижения", "награды", "сертификаты"}},
  {"languages", {"languages", "иностранные языки", "языки"}},
  {"publications", {"publications", "research", "research and publications", "исследования", "публикации"}},
};

std::string CaseFoldRussianAndAscii(const std::string& source) {
  std::string result;
  for (std::size_t index = 0; index < source.size();) {
    const unsigned char first = static_cast<unsigned char>(source[index]);
    if (first < 0x80) {
      result.push_back(static_cast<char>(std::tolower(first)));
      ++index;
      continue;
    }
    if (index + 1 < source.size() && first == 0xD0) {
      const unsigned char second = static_cast<unsigned char>(source[index + 1]);
      if (second == 0x81) {
        result.append("\xD1\x91");
        index += 2;
        continue;
      }
      if (second >= 0x90 && second <= 0x9F) {
        result.push_back(static_cast<char>(0xD0));
        result.push_back(static_cast<char>(second + 0x20));
        index += 2;
        continue;
      }
      if (second >= 0xA0 && second <= 0xAF) {
        result.push_back(static_cast<char>(0xD1));
        result.push_back(static_cast<char>(second - 0x20));
        index += 2;
        continue;
      }
    }
    result.push_back(source[index]);
    if (index + 1 < source.size()) {
      result.push_back(source[index + 1]);
      index += 2;
    } else {
      ++index;
    }
  }
  return result;
}

std::string NormalizeHeading(const std::string& source) {
  std::string normalized = CaseFoldRussianAndAscii(source);
  normalized = std::regex_replace(normalized, std::regex(R"(^\s*(?:\d{1,2}|[ivx]{1,5})[.)\s/-]+)", std::regex::icase), "");
  normalized = std::regex_replace(normalized, std::regex(R"([\s:|/\\._-]+)"), " ");
  normalized = std::regex_replace(normalized, std::regex(R"(^\s+|\s+$)"), "");
  return normalized;
}

std::optional<std::string> ClassifyHeading(const std::string& line) {
  const std::size_t colon_position = line.find(':');
  const std::string heading_source = colon_position == std::string::npos ? line : line.substr(0, colon_position);
  const std::string normalized_heading = NormalizeHeading(heading_source);
  for (const auto& [section_name, aliases] : kHeadingAliases) {
    if (std::find(aliases.begin(), aliases.end(), normalized_heading) != aliases.end()) {
      return section_name;
    }
  }
  return std::nullopt;
}

std::string DetectLayoutFamily(const ResumeLayout& layout, const std::vector<std::string>& section_order) {
  if (layout.sections.contains("publications")) {
    return "academic";
  }
  const auto skills = std::find(section_order.begin(), section_order.end(), "skills");
  const auto experience = std::find(section_order.begin(), section_order.end(), "experience");
  if (skills != section_order.end() && experience != section_order.end()) {
    return skills < experience ? "functional" : "combination";
  }
  if (experience != section_order.end()) {
    return "chronological";
  }
  return "unstructured";
}

}  // namespace

ResumeLayout ParseResumeLayout(const std::vector<std::string>& extracted_lines) {
  ResumeLayout layout;
  std::optional<std::string> current_section;
  std::vector<std::string> section_order;

  for (const std::string& line : extracted_lines) {
    const std::optional<std::string> heading = ClassifyHeading(line);
    if (heading.has_value()) {
      current_section = heading;
      layout.sections.try_emplace(heading.value());
      section_order.push_back(heading.value());

      const std::size_t colon_position = line.find(':');
      if (colon_position != std::string::npos && colon_position + 1 < line.size()) {
        layout.sections[heading.value()].push_back(line.substr(colon_position + 1));
      }
      continue;
    }
    if (current_section.has_value()) {
      layout.sections[current_section.value()].push_back(line);
    } else {
      layout.header_lines.push_back(line);
    }
  }

  layout.family = DetectLayoutFamily(layout, section_order);
  return layout;
}

ResumeLayout ParseResumeLayoutFromPdfFile(const std::filesystem::path& pdf_path) {
  return ParseResumeLayout(ExtractLinesFromPdfFile(pdf_path));
}

}  // namespace portfolio_cv_importer
