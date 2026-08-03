import { ProjectCard } from "../molecules/project-card";
import type { ProjectCardViewModel } from "../../types/domain";

interface ProjectGridProps {
  projects: ProjectCardViewModel[];
}

/**
 * Сетка проектов.
 */
export function ProjectGrid({ projects }: ProjectGridProps) {
  return (
    <div className="project-grid">
      {projects.map((projectViewModel) => (
        <ProjectCard key={projectViewModel.id} viewModel={projectViewModel} />
      ))}
    </div>
  );
}
