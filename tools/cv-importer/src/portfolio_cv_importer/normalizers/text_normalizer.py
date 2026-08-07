"""Нормализаторы строк и текстовых документов резюме."""

from __future__ import annotations

import re
import unicodedata

PERIOD_PATTERN = re.compile(
    r"(?:"
    r"(?:январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь|"
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}"
    r"|(?:19|20)\d{2}\s*(?:-|to|по|до)\s*(?:(?:19|20)\d{2}|present|current|now|н\.\s*в\.|настоящее время)"
    r"|(?:19|20)\d{2}"
    r")",
    flags=re.IGNORECASE,
)


def normalize_extracted_line(raw_line: str) -> str:
    """Нормализует строку после извлечения из PDF/Markdown/TXT и восстанавливает базовые пробелы."""

    normalized_line = unicodedata.normalize("NFKC", raw_line)
    normalized_line = normalized_line.replace("\t", " | ")
    normalized_line = normalized_line.replace("\u00a0", " ").replace("\u00ad", "")
    normalized_line = normalized_line.replace("\u200b", "").replace("\ufeff", "")
    normalized_line = normalized_line.replace("—", "-").replace("–", "-").replace("−", "-")
    normalized_line = re.sub(r"\s+", " ", normalized_line)
    for _ in range(3):
        normalized_line = re.sub(r"\b([A-ZА-ЯЁ]{2,})\s+([A-ZА-ЯЁ])\b", r"\1\2", normalized_line)
    normalized_line = re.sub(r"\b((?:19|20)\d)\s+(\d)\b", r"\1\2", normalized_line)
    normalized_line = re.sub(r"([А-Яа-яA-Za-z])(\d)", r"\1 \2", normalized_line)
    normalized_line = re.sub(r"(\d)([А-Яа-яA-Za-z])", r"\1 \2", normalized_line)
    return normalized_line.strip()


def normalize_resume_structural_line(raw_line: str) -> str:
    """Убирает markdown/HTML-префиксы, но сохраняет bullet-структуру для парсинга секций."""

    normalized_line = raw_line.strip()
    if not normalized_line:
        return ""

    normalized_line = re.sub(r"^\s*#{1,6}\s+", "", normalized_line)
    if re.match(r"^\s*[-*]\s+", normalized_line):
        normalized_line = f"• {re.sub(r'^\s*[-*]\s+', '', normalized_line)}"

    return normalize_extracted_line(normalized_line)


def normalize_resume_source_lines(raw_text: str) -> list[str]:
    """Снимает с текстового резюме markdown/HTML-шум и превращает документ в список строк."""

    html_normalized_text = raw_text
    html_normalized_text = re.sub(r"<br\s*/?>", "\n", html_normalized_text, flags=re.IGNORECASE)
    html_normalized_text = re.sub(r"</(p|li|h\d)>", "\n", html_normalized_text, flags=re.IGNORECASE)
    html_normalized_text = re.sub(r"<[^>]+>", " ", html_normalized_text)

    normalized_lines = []
    for raw_line in html_normalized_text.splitlines():
        normalized_line = normalize_resume_structural_line(raw_line)
        if normalized_line:
            normalized_lines.append(normalized_line)

    return normalized_lines
