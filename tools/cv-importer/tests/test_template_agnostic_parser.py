"""Контрактные тесты независимого от шаблона CV parser."""

from __future__ import annotations

import unittest

from portfolio_cv_importer.parsers.resume_portfolio_mapper import build_portfolio_payload_from_resume_sections
from portfolio_cv_importer.parsers.resume_section_parser import split_resume_sections


class TemplateAgnosticParserTestCase(unittest.TestCase):
    def test_parses_english_functional_cv_with_inline_skills(self) -> None:
        sections = split_resume_sections(
            [
                "Alex Morgan",
                "Platform Engineer",
                "alex@example.com | https://github.com/alex",
                "Technical skills: Python, PostgreSQL, Kubernetes",
                "Professional experience",
                "Example Systems",
                "Senior Engineer",
                "2022 - Present",
                "• Designed a distributed event pipeline",
                "Education",
                "Example University",
                "2017 - 2021",
            ],
        )

        self.assertEqual(sections.detected_layout, "functional")
        self.assertEqual(sections.section_lines["skills"], ["Python, PostgreSQL, Kubernetes"])
        payload = build_portfolio_payload_from_resume_sections(sections)
        self.assertEqual(payload["profile"]["displayName"]["en"], "Alex Morgan")
        self.assertEqual(payload["skills"]["focusAreas"], ["Python", "PostgreSQL", "Kubernetes"])
        self.assertNotIn("Dmitry", str(payload))

    def test_parses_russian_chronological_resume_without_named_rules(self) -> None:
        sections = split_resume_sections(
            [
                "Иван Петров",
                "Системный аналитик",
                "Казань, Россия",
                "01. Опыт работы",
                "Компания Пример",
                "Системный аналитик",
                "2023 - настоящее время",
                "• Проектирование API и моделей данных",
                "Образование",
                "Технический университет",
                "2018 - 2022",
                "Навыки",
                "Инструменты: SQL; BPMN; Kafka",
                "Сертификаты",
                "• Архитектура API",
            ],
        )

        self.assertEqual(sections.detected_layout, "combination")
        payload = build_portfolio_payload_from_resume_sections(sections)
        self.assertEqual(payload["profile"]["displayName"]["ru"], "Иван Петров")
        self.assertEqual(payload["experience"][0]["company"]["ru"], "Компания Пример")
        self.assertEqual(payload["skills"]["groups"][0]["items"], ["SQL", "BPMN", "Kafka"])
        self.assertNotIn("Fillusion", str(payload))


if __name__ == "__main__":
    unittest.main()
