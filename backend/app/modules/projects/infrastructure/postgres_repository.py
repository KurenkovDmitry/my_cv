"""Заглушка PostgreSQL-репозитория для модуля projects."""

from app.modules.projects.domain.entities import Project


class InMemoryProjectRepository:
    """Временная реализация репозитория для старта frontend/backend контракта."""

    async def list_featured(self) -> list[Project]:
        return [
            Project(
                identifier="portfolio-platform",
                slug="portfolio-platform",
                title_ru="Платформа персонального портфолио",
                title_en="Personal portfolio platform",
                summary_ru=(
                    "Модульный проект с публичной витриной, админкой и безопасным backend-контуром."
                ),
                summary_en=(
                    "A modular project with a public showcase, admin panel, and secure backend layer."
                ),
                featured=True,
                technologies=("TypeScript", "React", "FastAPI", "PostgreSQL", "Redis"),
            )
        ]

