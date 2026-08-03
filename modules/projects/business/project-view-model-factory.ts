import type { LocaleCode } from "@portfolio/shared-types";
import { LocaleService } from "@portfolio/modules/localization";
import type { ProjectContent } from "@portfolio/shared-types";
import type { ProjectCardViewModel } from "../types/domain";

/**
 * Фабрика карточек проекта для UI.
 */
export class ProjectViewModelFactory {
  public constructor(private readonly localeService: LocaleService) {}

  public createCardViewModel(project: ProjectContent, localeCode: LocaleCode): ProjectCardViewModel {
    return {
      id: project.id,
      title: this.localeService.translate(project.title, localeCode),
      summary: this.localeService.translate(project.summary, localeCode),
      technologies: project.technologies,
      links: project.links.map((projectLink) => ({
        kind: projectLink.kind,
        label: this.localeService.translate(projectLink.label, localeCode),
        href: projectLink.href,
      })),
    };
  }
}

