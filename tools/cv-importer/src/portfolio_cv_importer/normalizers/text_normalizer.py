"""Нормализаторы строк и текстовых документов резюме."""

from __future__ import annotations

import re

PERIOD_PATTERN = re.compile(
    r"(Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август|Сентябрь|Октябрь|Ноябрь|Декабрь|[A-Za-z]+)\s*\d{4}",
)


def normalize_extracted_line(raw_line: str) -> str:
    """Нормализует строку после извлечения из PDF/Markdown/TXT и восстанавливает базовые пробелы."""

    normalized_line = raw_line
    replacement_pairs = (
        ("Языкипрограммированияифреймворки", "Языки программирования и фреймворки"),
        ("Технологии:", "Технологии:"),
        ("Управлениепроектами", "Управление проектами"),
        ("Личныекачества", "Личные качества"),
        ("Сертификатыирекомендации", "Сертификаты и рекомендации"),
        ("УЧЕБНЫЕПРОЕКТЫ", "УЧЕБНЫЕ ПРОЕКТЫ"),
        ("Бауманскаяинженернаяшкола", "Бауманская инженерная школа"),
        ("Московскийгосударственныйтехническийуниверситет", "Московский государственный технический университет"),
        ("Производственнаяпрактика", "Производственная практика"),
        ("инженернойшколе", "инженерной школе"),
        ("поднагрузкой", "под нагрузкой"),
    )

    for source_fragment, target_fragment in replacement_pairs:
        normalized_line = normalized_line.replace(source_fragment, target_fragment)

    normalized_line = normalized_line.replace("\u00a0", " ")
    normalized_line = re.sub(r"\s+", " ", normalized_line)
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
