import type { LocaleCode } from "@portfolio/shared-types";
import { ProjectContentFacade } from "../api/project-content-facade";
import { ProjectViewModelFactory } from "./project-view-model-factory";
import type { ProjectCardViewModel } from "../types/domain";

/**
 * Прикладной сервис сценариев блока проектов.
 */
export class ProjectBusinessService {
  public constructor(
    private readonly projectContentFacade: ProjectContentFacade,
    private readonly projectViewModelFactory: ProjectViewModelFactory,
  ) {}

  public getFeaturedProjectCards(localeCode: LocaleCode): ProjectCardViewModel[] {
    return this.projectContentFacade
      .getFeaturedProjects()
      .map((project) => this.projectViewModelFactory.createCardViewModel(project, localeCode));
  }
}

