"""Response-модели модуля projects."""

from pydantic import BaseModel, Field


class ProjectListItemResponse(BaseModel):
    """Ответ одной карточки проекта."""

    id: str = Field(description="Идентификатор проекта.")
    slug: str = Field(description="Человекочитаемый slug проекта.")
    title: str = Field(description="Локализованное название проекта.")
    summary: str = Field(description="Локализованное краткое описание проекта.")
    featured: bool = Field(description="Признак попадания в hero-подборку.")
    technologies: tuple[str, ...] = Field(description="Список использованных технологий.")


class ProjectListResponse(BaseModel):
    """Ответ списка проектов."""

    items: list[ProjectListItemResponse]
    total: int

