"""Pure Python extractor строк из PDF без OCR."""

from __future__ import annotations

import re
import zlib

from portfolio_cv_importer.normalizers.text_normalizer import normalize_extracted_line


def extract_lines_from_pdf_bytes(pdf_bytes: bytes) -> list[str]:
    """Извлекает человекочитаемые строки из PDF через ToUnicode-карты."""

    pdf_objects = parse_pdf_objects(pdf_bytes)
    font_to_unicode_maps = build_font_to_unicode_maps(pdf_objects)
    page_lines: list[str] = []

    for body_text in pdf_objects.values():
        if not re.search(r"/Type/Page\b", body_text):
            continue

        content_reference_match = re.search(r"/Contents\s+(\d+)\s+0\s+R", body_text)
        if content_reference_match is None:
            continue

        page_font_references = parse_page_font_references(body_text)
        content_object = pdf_objects.get(int(content_reference_match.group(1)))
        if content_object is None:
            continue

        content_stream = inflate_object_stream(content_object)
        if content_stream is None:
            continue

        text_items = extract_text_items(content_stream, page_font_references, font_to_unicode_maps)
        page_lines.extend(group_text_items_into_lines(text_items))

    normalized_lines = [normalize_extracted_line(line) for line in page_lines]
    return [line for line in normalized_lines if line]


def parse_pdf_objects(pdf_bytes: bytes) -> dict[int, str]:
    """Извлекает все объекты PDF как блоки latin1-текста."""

    pdf_text = pdf_bytes.decode("latin1")
    object_pattern = re.compile(r"(\d+)\s+(\d+)\s+obj")
    pdf_objects: dict[int, str] = {}

    for object_match in object_pattern.finditer(pdf_text):
        object_id = int(object_match.group(1))
        body_start = object_match.end()
        object_end = pdf_text.find("endobj", body_start)
        if object_end == -1:
            continue

        pdf_objects[object_id] = pdf_text[body_start:object_end]

    return pdf_objects


def inflate_object_stream(body_text: str) -> str | None:
    """Разжимает stream-часть PDF-объекта."""

    stream_index = body_text.find("stream")
    if stream_index == -1:
        return None

    stream_start_index = stream_index + len("stream")
    if body_text[stream_start_index:stream_start_index + 2] == "\r\n":
        stream_start_index += 2
    elif body_text[stream_start_index:stream_start_index + 1] == "\n":
        stream_start_index += 1

    stream_end_index = body_text.find("endstream", stream_start_index)
    if stream_end_index == -1:
        return None

    normalized_end_index = stream_end_index
    if body_text[normalized_end_index - 1:normalized_end_index] == "\n":
        normalized_end_index -= 1
    if body_text[normalized_end_index - 1:normalized_end_index] == "\r":
        normalized_end_index -= 1

    compressed_bytes = body_text[stream_start_index:normalized_end_index].encode("latin1")
    return zlib.decompress(compressed_bytes).decode("utf-8")


def build_font_to_unicode_maps(pdf_objects: dict[int, str]) -> dict[int, dict[str, str]]:
    """Строит карту фонтов и соответствующих ToUnicode-таблиц."""

    font_maps: dict[int, dict[str, str]] = {}

    for object_id, body_text in pdf_objects.items():
        to_unicode_match = re.search(r"/ToUnicode\s+(\d+)\s+0\s+R", body_text)
        if to_unicode_match is None:
            continue

        unicode_object = pdf_objects.get(int(to_unicode_match.group(1)))
        if unicode_object is None:
            continue

        unicode_stream = inflate_object_stream(unicode_object)
        if unicode_stream is None:
            continue

        font_maps[object_id] = parse_to_unicode_map(unicode_stream)

    return font_maps


def parse_to_unicode_map(unicode_stream: str) -> dict[str, str]:
    """Читает ToUnicode CMap и превращает его в словарь символов."""

    unicode_map: dict[str, str] = {}
    blocks = re.findall(r"(?:\d+)\s+begin(?:bfchar|bfrange)[\s\S]*?end(?:bfchar|bfrange)", unicode_stream)
    for block in blocks:
        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        for block_line in block_lines:
            char_match = re.match(r"^<([0-9A-F]+)>\s+<([0-9A-F]+)>$", block_line, flags=re.IGNORECASE)
            if char_match:
                unicode_map[char_match.group(1).upper()] = unicode_from_hex(char_match.group(2))
                continue

            range_match = re.match(
                r"^<([0-9A-F]+)>\s+<([0-9A-F]+)>\s+<([0-9A-F]+)>$",
                block_line,
                flags=re.IGNORECASE,
            )
            if range_match:
                range_start = int(range_match.group(1), 16)
                range_end = int(range_match.group(2), 16)
                target_code = int(range_match.group(3), 16)
                for source_code in range(range_start, range_end + 1):
                    unicode_map[source_code_to_key(source_code, len(range_match.group(1)))] = unicode_from_hex(
                        format(target_code, "x"),
                    )
                    target_code += 1
                continue

            array_match = re.match(
                r"^<([0-9A-F]+)>\s+<([0-9A-F]+)>\s+\[(.+)\]$",
                block_line,
                flags=re.IGNORECASE,
            )
            if array_match is None:
                continue

            range_start = int(array_match.group(1), 16)
            unicode_targets = re.findall(r"<([0-9A-F]+)>", array_match.group(3), flags=re.IGNORECASE)
            for target_index, unicode_target in enumerate(unicode_targets):
                unicode_map[source_code_to_key(range_start + target_index, len(array_match.group(1)))] = unicode_from_hex(
                    unicode_target,
                )

    return unicode_map


def parse_page_font_references(body_text: str) -> dict[str, int]:
    """Разбирает справочник font-ресурсов конкретной страницы."""

    font_references: dict[str, int] = {}
    font_block_match = re.search(r"/Font\s*<<([\s\S]*?)>>", body_text)
    if font_block_match is None:
        return font_references

    for font_match in re.finditer(r"/(F\d+)\s+(\d+)\s+0\s+R", font_block_match.group(1)):
        font_references[font_match.group(1)] = int(font_match.group(2))

    return font_references


def extract_text_items(
    content_stream: str,
    page_font_references: dict[str, int],
    font_to_unicode_maps: dict[int, dict[str, str]],
) -> list[dict[str, object]]:
    """Извлекает текстовые элементы с координатами для последующей сборки строк."""

    text_items: list[dict[str, object]] = []
    current_font_name: str | None = None
    current_text_x = 0.0
    current_text_y = 0.0

    for content_line in content_stream.splitlines():
        font_match = re.search(r"/(F\d+)\s+[\d.]+\s+Tf", content_line)
        if font_match is not None:
            current_font_name = font_match.group(1)

        transform_match = re.search(
            r"([\d.-]+)\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)\s+Tm",
            content_line,
        )
        if transform_match is not None:
            current_text_x = float(transform_match.group(2))
            current_text_y = float(transform_match.group(3))

        unicode_map: dict[str, str] = {}
        if current_font_name is not None and current_font_name in page_font_references:
            unicode_map = font_to_unicode_maps.get(page_font_references[current_font_name], {})

        for array_match in re.finditer(r"\[(.*?)\]\s*TJ", content_line):
            decoded_text = decode_pdf_array_text(array_match.group(1), unicode_map)
            if decoded_text.strip():
                text_items.append({"x": current_text_x, "y": current_text_y, "text": decoded_text})

        for literal_match in re.finditer(r"\(((?:\\.|[^\\)])*)\)\s*Tj", content_line):
            decoded_text = decode_pdf_literal_text(literal_match.group(1))
            if decoded_text.strip():
                text_items.append({"x": current_text_x, "y": current_text_y, "text": decoded_text})

        for hex_match in re.finditer(r"<([0-9A-F]+)>\s*Tj", content_line, flags=re.IGNORECASE):
            decoded_text = decode_pdf_hex_text(hex_match.group(1), unicode_map)
            if decoded_text.strip():
                text_items.append({"x": current_text_x, "y": current_text_y, "text": decoded_text})

    return text_items


def group_text_items_into_lines(text_items: list[dict[str, object]]) -> list[str]:
    """Группирует отдельные текстовые элементы в строки документа."""

    sorted_items = sorted(
        text_items,
        key=lambda item: (-float(item["y"]), float(item["x"])),
    )
    grouped_lines: list[dict[str, object]] = []

    for text_item in sorted_items:
        same_line = next(
            (line for line in grouped_lines if abs(float(line["y"]) - float(text_item["y"])) < 2.5),
            None,
        )
        if same_line is None:
            grouped_lines.append({"y": text_item["y"], "items": [text_item]})
        else:
            same_line["items"].append(text_item)

    result_lines: list[str] = []
    for grouped_line in sorted(grouped_lines, key=lambda line: -float(line["y"])):
        line_text = "".join(
            str(item["text"])
            for item in sorted(grouped_line["items"], key=lambda line_item: float(line_item["x"]))
        )
        line_text = re.sub(r"\s+", " ", line_text).strip()
        if line_text:
            result_lines.append(line_text)

    return result_lines


def decode_pdf_array_text(array_source: str, unicode_map: dict[str, str]) -> str:
    """Декодирует массив TJ с hex- и literal-токенами."""

    token_pattern = re.compile(r"<([0-9A-F]+)>|\(((?:\\.|[^\\)])*)\)|(-?\d+(?:\.\d+)?)", flags=re.IGNORECASE)
    decoded_fragments: list[str] = []

    for token_match in token_pattern.finditer(array_source):
        if token_match.group(1):
            decoded_fragments.append(decode_pdf_hex_text(token_match.group(1), unicode_map))
            continue

        if token_match.group(2):
            decoded_fragments.append(decode_pdf_literal_text(token_match.group(2)))

    return "".join(decoded_fragments)


def decode_pdf_literal_text(literal_text: str) -> str:
    """Декодирует literal-строку PDF."""

    return (
        literal_text
        .replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
        .replace(r"\\", "\\")
    )


def decode_pdf_hex_text(hex_text: str, unicode_map: dict[str, str]) -> str:
    """Декодирует hex-последовательность PDF через ToUnicode-карту."""

    normalized_hex = hex_text.upper()
    glyph_chunks = re.findall(r".{1,4}", normalized_hex)
    return "".join(unicode_map.get(glyph_chunk, "") for glyph_chunk in glyph_chunks)


def source_code_to_key(source_code: int, width: int) -> str:
    """Преобразует числовой код символа в hex-ключ CMap фиксированной ширины."""

    return format(source_code, "x").upper().zfill(width)


def unicode_from_hex(unicode_hex: str) -> str:
    """Преобразует hex-код Unicode в Python-символ."""

    return chr(int(unicode_hex, 16))
