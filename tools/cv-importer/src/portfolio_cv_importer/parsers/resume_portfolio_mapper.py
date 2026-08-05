"""Маппинг секций резюме в `portfolio.v1`."""

from __future__ import annotations

from portfolio_cv_importer.domain.default_portfolio_factory import create_base_portfolio_payload
from portfolio_cv_importer.domain.models import ResumeEntry, ResumeSections
from portfolio_cv_importer.parsers.resume_section_parser import collect_bullet_entries


def build_portfolio_payload_from_resume_sections(resume_sections: ResumeSections) -> dict[str, object]:
    """Собирает итоговый `portfolio.v1` из нормализованных секций резюме."""

    portfolio_payload = create_base_portfolio_payload(
        display_name_ru="Дмитрий Андреевич Куренков",
        display_name_en="Dmitry Andreevich Kurenkov",
        headline_ru="Системный аналитик и platform-инженер, который проектирует highload-сервисы, данные и рабочие интерфейсы.",
        headline_en="System analyst and platform-minded engineer focused on highload services, data architecture, and production-grade interfaces.",
        location_ru=resume_sections.location_ru,
        location_en=resume_sections.location_en,
    )
    portfolio_payload["education"] = collect_mapped_education_entries(resume_sections)
    portfolio_payload["experience"] = collect_mapped_experience_entries(resume_sections)
    portfolio_payload["projects"] = collect_mapped_project_entries(resume_sections)
    return portfolio_payload


def collect_mapped_education_entries(resume_sections: ResumeSections) -> list[dict[str, object]]:
    """Преобразует блок образования в массив элементов портфолио."""

    mapped_entries: list[dict[str, object]] = []
    for entry in collect_bullet_entries(resume_sections.education_lines):
        mapped_entry = map_education_entry(entry)
        if mapped_entry is not None:
            mapped_entries.append(mapped_entry)

    return mapped_entries


def collect_mapped_experience_entries(resume_sections: ResumeSections) -> list[dict[str, object]]:
    """Преобразует блок опыта в массив элементов портфолио."""

    mapped_entries: list[dict[str, object]] = []
    for entry in collect_bullet_entries(resume_sections.experience_lines):
        mapped_entry = map_experience_entry(entry)
        if mapped_entry is not None:
            mapped_entries.append(mapped_entry)

    return mapped_entries


def collect_mapped_project_entries(resume_sections: ResumeSections) -> list[dict[str, object]]:
    """Преобразует блоки проектов и учебных проектов в карточки портфолио."""

    mapped_entries: list[dict[str, object]] = []
    raw_entries = collect_bullet_entries(resume_sections.project_lines) + collect_bullet_entries(
        resume_sections.study_project_lines,
    )

    for entry in raw_entries:
        mapped_entry = map_project_entry(entry)
        if mapped_entry is not None:
            mapped_entries.append(mapped_entry)

    return mapped_entries


def map_education_entry(entry: ResumeEntry) -> dict[str, object] | None:
    """Преобразует запись образования в локализованный блок портфолио."""

    if "Высшая школа экономики" in entry.text:
        return {
            "id": "hse-netology-master",
            "title": {
                "ru": "НИУ ВШЭ, магистратура ФКН и Нетология",
                "en": "HSE University, Faculty of Computer Science master's track with Netology",
            },
            "status": "draft",
        }

    if "VK" in entry.text or "Веб-разработка" in entry.text:
        return {
            "id": "vk-bmstu-web",
            "title": {
                "ru": "Образовательный центр VK в МГТУ им. Н. Э. Баумана",
                "en": "VK Education Center at Bauman Moscow State Technical University",
            },
            "status": "published",
        }

    if "Красный диплом" in entry.text:
        return {
            "id": "bmstu-bachelor",
            "title": {
                "ru": "МГТУ им. Н. Э. Баумана, бакалавриат ИУ, красный диплом",
                "en": "Bauman Moscow State Technical University, bachelor's degree in informatics and control systems with honors",
            },
            "status": "published",
        }

    if "1580" in entry.text:
        return {
            "id": "school-1580",
            "title": {
                "ru": "Бауманская инженерная школа №1580, профиль информатика",
                "en": "Bauman Engineering School No. 1580, informatics profile",
            },
            "status": "published",
        }

    return None


def map_experience_entry(entry: ResumeEntry) -> dict[str, object] | None:
    """Преобразует запись опыта в локализованный блок портфолио."""

    if "ТБанк" in entry.text or "Т-Банк" in entry.text:
        return {
            "id": "t-bank-credit-products",
            "company": {
                "ru": "Т-Банк",
                "en": "T-Bank",
            },
            "role": {
                "ru": f"Стажёр-системный аналитик. {entry.text}",
                "en": "System analyst intern in the credit products domain with SQL, Java Spring, requirements analysis, and testing.",
            },
            "status": "published",
        }

    if "Латеко" in entry.text and "FlexiKanban" in entry.text:
        return {
            "id": "lateco-project-experience",
            "company": {
                "ru": "Латеко и внутренние IT-проекты",
                "en": "Lateco and internal IT initiatives",
            },
            "role": {
                "ru": "System analyst с дополнительной ролью backend-архитектора, full-stack разработчика и тестировщика на внутренних продуктах компании.",
                "en": "System analyst with additional responsibilities across backend architecture, full-stack delivery, and QA for internal products.",
            },
            "status": "published",
        }

    if "Производственная практика" in entry.text:
        return {
            "id": "lateco-practice",
            "company": {
                "ru": "Латеко, производственная практика",
                "en": "Lateco internship practice",
            },
            "role": {
                "ru": "Участие в разработке целевой архитектуры и детального плана цифровой трансформации для единой IT-компании холдинга.",
                "en": "Worked on target architecture and a detailed transformation roadmap for a unified IT company across a holding structure.",
            },
            "status": "published",
        }

    return None


def map_project_entry(entry: ResumeEntry) -> dict[str, object] | None:
    """Преобразует запись проекта в карточку портфолио."""

    if "Fillusion" in entry.text:
        return {
            "id": "fillusion",
            "slug": "fillusion",
            "featured": True,
            "status": "active",
            "title": {
                "ru": "Fillusion",
                "en": "Fillusion",
            },
            "summary": {
                "ru": "Платформа автозаполнения и редактирования баз данных с AI и Faker: микросервисная архитектура, gRPC, Kafka, backend-функциональность, Docker Compose, CI/CD и Nginx.",
                "en": "AI-assisted database autofill and editing platform combining microservices, gRPC, Kafka, backend delivery, Docker Compose, CI/CD, and Nginx.",
            },
            "technologies": ["Go", "Python", "Java Spring", "gRPC", "Kafka", "Docker Compose", "CI/CD", "Nginx"],
            "links": [],
        }

    if "FlexiKanban" in entry.text:
        return {
            "id": "flexi-kanban",
            "slug": "flexi-kanban",
            "featured": True,
            "status": "active",
            "title": {
                "ru": "FlexiKanban",
                "en": "FlexiKanban",
            },
            "summary": {
                "ru": "Веб-сервис для управления проектами: Kanban-доски, задачи, чаты и уведомления с backend-архитектурой, админ-панелью, интеграциями и несколькими моделями данных.",
                "en": "Project management platform with Kanban boards, tasks, chats, and notifications built around backend architecture, admin tooling, integrations, and multi-database modeling.",
            },
            "technologies": ["Go", "Python", "Java Spring", "Kanban", "Admin UI", "API design", "Security"],
            "links": [],
        }

    if "Split-app" in entry.text or "SplitAppTg_bot" in entry.text:
        return {
            "id": "split-app",
            "slug": "split-app",
            "featured": True,
            "status": "active",
            "title": {
                "ru": "Split-app",
                "en": "Split-app",
            },
            "summary": {
                "ru": "Telegram-приложение для разделения и оплаты счетов с доработкой PostgreSQL под нагрузку, развитием backend-логики на Python и призовыми результатами на The Open League.",
                "en": "Telegram-based bill splitting app with PostgreSQL redesign for higher load, Python backend evolution, and award-winning results in The Open League.",
            },
            "technologies": ["Python", "PostgreSQL", "Telegram", "Performance tuning"],
            "links": [
                {
                    "kind": "demo",
                    "label": {
                        "ru": "Telegram-бот",
                        "en": "Telegram bot",
                    },
                    "href": "https://t.me/SplitAppTg_bot",
                },
            ],
        }

    if "Twirly-Quirly" in entry.text:
        return {
            "id": "twirly-quirly",
            "slug": "twirly-quirly",
            "featured": False,
            "status": "active",
            "title": {
                "ru": "Twirly-Quirly",
                "en": "Twirly-Quirly",
            },
            "summary": {
                "ru": "Маркетплейс с рейтинговой системой продавцов, где зона ответственности охватывала бизнес-требования, пользовательские сценарии и QA-проверку функциональности.",
                "en": "Marketplace with a seller rating system where the scope covered business requirements, user scenarios, and QA validation.",
            },
            "technologies": ["System analysis", "QA", "User scenarios", "Product requirements"],
            "links": [],
        }

    if "Highload Ozon" in entry.text:
        return {
            "id": "highload-ozon",
            "slug": "highload-ozon",
            "featured": False,
            "status": "active",
            "title": {
                "ru": "Highload Ozon",
                "en": "Highload Ozon",
            },
            "summary": {
                "ru": "Учебное проектирование высоконагруженного интернет-магазина: MAU/DAU, RPS, сетевой трафик, балансировка, модели БД, шардинг, кэширование и отказоустойчивость.",
                "en": "Highload e-commerce architecture study covering MAU/DAU, RPS, traffic budgeting, balancing, database design, sharding, caching, and resilience.",
            },
            "technologies": ["Highload", "Sharding", "Caching", "Architecture", "Database design"],
            "links": [
                {
                    "kind": "repository",
                    "label": {
                        "ru": "GitHub",
                        "en": "GitHub",
                    },
                    "href": "https://github.com/KurenkovDmitry/highload-ozon",
                },
            ],
        }

    if "государственной регистрации" in entry.text:
        return {
            "id": "kanban-board-register",
            "slug": "kanban-board-register",
            "featured": False,
            "status": "active",
            "title": {
                "ru": "Канбан-доска",
                "en": "Kanban board",
            },
            "summary": {
                "ru": "Зарегистрированная программа для ЭВМ с backend на Java/Spring, frontend на JavaScript, совместной работой и встроенными методами анализа MoSCoW и Kano.",
                "en": "Registered software product with Java/Spring backend, JavaScript frontend, collaboration workflows, and embedded MoSCoW and Kano analysis methods.",
            },
            "technologies": ["Java", "Spring", "JavaScript", "MoSCoW", "Kano"],
            "links": [],
        }

    if "OXIC" in entry.text:
        return {
            "id": "oxic-marketplace",
            "slug": "oxic-marketplace",
            "featured": False,
            "status": "active",
            "title": {
                "ru": "OXIC",
                "en": "OXIC",
            },
            "summary": {
                "ru": "Маркетплейс с frontend-фокусом на TypeScript, участием в backend на Go, UI-дизайном в Figma и базовой серверной конфигурацией для деплоя через Nginx.",
                "en": "Marketplace project with a TypeScript-heavy frontend, Go backend contribution, Figma UI design, and foundational Nginx deployment setup.",
            },
            "technologies": ["TypeScript", "Go", "Figma", "Nginx"],
            "links": [
                {
                    "kind": "repository",
                    "label": {
                        "ru": "Frontend",
                        "en": "Frontend",
                    },
                    "href": "https://github.com/frontend-park-mail-ru/2024_2_kotyari",
                },
                {
                    "kind": "repository",
                    "label": {
                        "ru": "Backend",
                        "en": "Backend",
                    },
                    "href": "https://github.com/go-park-mail-ru/2024_2_kotyari",
                },
            ],
        }

    return None
