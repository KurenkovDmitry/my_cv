import { SectionHeading } from "@portfolio/shared-ui";
import { ProjectGrid } from "../organisms/project-grid";
import type { ProjectCardViewModel } from "../../types/domain";

interface ProjectsPageProps {
  localeCode: "ru" | "en";
  projects: ProjectCardViewModel[];
}

/**
 * Страница проектной витрины.
 */
export function ProjectsPage({ localeCode, projects }: ProjectsPageProps) {
  return (
    <section className="projects-section">
      <SectionHeading
        eyebrow={localeCode === "ru" ? "Проекты" : "Projects"}
        title={localeCode === "ru" ? "Первый vertical slice уже готов к развитию." : "The first vertical slice is ready to grow."}
        description={
          localeCode === "ru"
            ? "Компонент projects используется как эталон для дальнейшего масштабирования архитектуры."
            : "The projects component acts as the reference implementation for future architecture growth."
        }
      />
      <ProjectGrid projects={projects} />
    </section>
  );
}
