import { useMemo, useState } from "react";
import type { RegionalLocaleCode } from "@portfolio/modules/localization";
import { ProjectGrid } from "../organisms/project-grid";
import type { ProjectCardViewModel } from "../../types/domain";

interface ProjectsPageProps {
  regionalLocale: RegionalLocaleCode;
  projects: ProjectCardViewModel[];
}

type ProjectFilter = "all" | "commercial" | "academic" | "hackathon";

/** Полная проектная история с фильтрами и раскрывающимися длинными описаниями. */
export function ProjectsPage({ regionalLocale, projects }: ProjectsPageProps) {
  const [filter, setFilter] = useState<ProjectFilter>("all");
  const isRussian = regionalLocale === "ru";
  const visibleProjects = useMemo(
    () => filter === "all" ? projects : projects.filter((project) => project.category === filter),
    [filter, projects],
  );

  const labels: Record<ProjectFilter, string> = isRussian
    ? { all: "Все", commercial: "Продуктовые", academic: "Учебные", hackathon: "Хакатоны" }
    : { all: "All", commercial: "Product", academic: "Academic", hackathon: "Hackathons" };

  return (
    <section className="projects-page">
      <header className="projects-page__hero">
        <p className="projects-page__eyebrow">Portfolio archive / 2023—2026</p>
        <div>
          <h1>{isRussian ? "Проекты без сокращений." : "Projects, without the shorthand."}</h1>
          <p>{isRussian
            ? "Семь кейсов из резюме: роли, состав команд, архитектурные решения, стек и измеримые результаты. Карточки рассчитаны и на более длинные описания."
            : "Seven CV cases with roles, team context, architecture work, technologies and measurable outcomes. Every card is designed to hold a longer case study."}</p>
        </div>
        <span className="projects-page__count">{String(projects.length).padStart(2, "0")}</span>
      </header>

      <div className="project-filters" aria-label={isRussian ? "Фильтр проектов" : "Project filters"}>
        {(Object.keys(labels) as ProjectFilter[]).map((filterKey) => (
          <button
            className={filter === filterKey ? "project-filters__button project-filters__button--active" : "project-filters__button"}
            type="button"
            key={filterKey}
            onClick={() => setFilter(filterKey)}
          >
            {labels[filterKey]}
            <span>{filterKey === "all" ? projects.length : projects.filter((project) => project.category === filterKey).length}</span>
          </button>
        ))}
      </div>

      <ProjectGrid projects={visibleProjects} isRussian={isRussian} />
    </section>
  );
}
