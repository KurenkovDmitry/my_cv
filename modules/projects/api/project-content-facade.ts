import type { PortfolioContent, ProjectContent } from "@portfolio/shared-types";

/**
 * Фасад доступа к данным проектов.
 */
export class ProjectContentFacade {
  public constructor(private readonly portfolioContent: PortfolioContent) {}

  public getFeaturedProjects(): ProjectContent[] {
    return this.portfolioContent.projects.filter((project) => project.featured);
  }

  public getAllProjects(): ProjectContent[] {
    return this.portfolioContent.projects;
  }
}

