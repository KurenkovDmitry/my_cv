import type { ProjectCardViewModel } from "../../types/domain";

interface ProjectCardProps {
  viewModel: ProjectCardViewModel;
}

/**
 * Карточка проекта для публичной витрины.
 */
export function ProjectCard({ viewModel }: ProjectCardProps) {
  return (
    <article className="project-card">
      <div className="project-card__header">
        <p className="project-card__kicker">Case study</p>
        <h3 className="project-card__title">{viewModel.title}</h3>
      </div>
      <p className="project-card__summary">{viewModel.summary}</p>
      <ul className="project-card__tech-list">
        {viewModel.technologies.map((technology) => (
          <li key={technology} className="project-card__tech">
            {technology}
          </li>
        ))}
      </ul>
      <div className="project-card__links">
        {viewModel.links.map((projectLink) => (
          <a key={projectLink.kind} href={projectLink.href} className="project-card__link">
            {projectLink.label}
          </a>
        ))}
      </div>
    </article>
  );
}
