import type { LocaleCode } from "@portfolio/shared-types";
import { resolveContentAssetUrl } from "@portfolio/shared-config";
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
      slug: project.slug,
      featured: project.featured,
      title: this.localeService.translate(project.title, localeCode),
      summary: this.localeService.translate(project.summary, localeCode),
      coverAsset: project.coverAssetId
        ? resolveContentAssetUrl(project.coverAssetId, "")
        : undefined,
      category: project.category,
      period: project.period ? this.localeService.translate(project.period, localeCode) : undefined,
      role: project.role ? this.localeService.translate(project.role, localeCode) : undefined,
      teamSize: project.teamSize,
      responsibilities: (project.responsibilities ?? []).map((item) =>
        this.localeService.translate(item, localeCode),
      ),
      achievements: (project.achievements ?? []).map((item) =>
        this.localeService.translate(item, localeCode),
      ),
      technologies: project.technologies,
      links: project.links.map((projectLink) => ({
        kind: projectLink.kind,
        label: this.localeService.translate(projectLink.label, localeCode),
        href: projectLink.href,
      })),
    };
  }
}
