import type { ProjectCardViewModel } from "../../types/domain";

interface ProjectCardProps {
  viewModel: ProjectCardViewModel;
  isRussian: boolean;
}

/** Карточка выдерживает короткое превью и длинный раскрытый кейс без изменения разметки. */
export function ProjectCard({ viewModel, isRussian }: ProjectCardProps) {
  const categoryLabel = {
    commercial: isRussian ? "Продукт" : "Product",
    academic: isRussian ? "Учебный" : "Academic",
    hackathon: isRussian ? "Хакатон" : "Hackathon",
  }[viewModel.category ?? "commercial"];

  return (
    <article className={`project-card project-card--${viewModel.category ?? "commercial"}`}>
      <header className="project-card__header">
        <div className="project-card__meta">
          <span>{categoryLabel}</span>
          <span>{viewModel.period}</span>
        </div>
        <h2 className="project-card__title">{viewModel.title}</h2>
        {viewModel.role ? <p className="project-card__role">{viewModel.role}</p> : null}
      </header>

      <p className="project-card__summary">{viewModel.summary}</p>

      {viewModel.achievements.length ? (
        <div className="project-card__impact">
          <span aria-hidden="true">↗</span>
          <strong>{viewModel.achievements[0]}</strong>
        </div>
      ) : null}

      <ul className="project-card__tech-list">
        {viewModel.technologies.map((technology) => (
          <li key={technology} className="project-card__tech">{technology}</li>
        ))}
      </ul>

      <details className="project-card__details">
        <summary>
          <span>{isRussian ? "Зона ответственности" : "Scope and contribution"}</span>
          <span className="project-card__details-icon" aria-hidden="true">+</span>
        </summary>
        <div className="project-card__details-content">
          {viewModel.teamSize ? <p><strong>{isRussian ? "Команда" : "Team"}:</strong> {viewModel.teamSize} {isRussian ? "чел." : "people"}</p> : null}
          {viewModel.responsibilities.length ? (
            <ul className="detail-list">
              {viewModel.responsibilities.map((responsibility) => <li key={responsibility}>{responsibility}</li>)}
            </ul>
          ) : <p>{isRussian ? "Подробности доступны в исходном резюме." : "Further detail is available in the source CV."}</p>}
          {viewModel.achievements.length > 1 ? (
            <ul className="project-card__achievements">
              {viewModel.achievements.slice(1).map((achievement) => <li key={achievement}>{achievement}</li>)}
            </ul>
          ) : null}
        </div>
      </details>

      {viewModel.links.length ? (
        <div className="project-card__links">
          {viewModel.links.map((projectLink) => (
            <a key={`${projectLink.kind}-${projectLink.href}`} href={projectLink.href} className="project-card__link" target="_blank" rel="noreferrer">
              {projectLink.label} <span aria-hidden="true">↗</span>
            </a>
          ))}
        </div>
      ) : null}
    </article>
  );
}
