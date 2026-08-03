import type { PortfolioContent } from "@portfolio/shared-types";

/**
 * Фасад чтения контента профиля.
 *
 * На первом этапе читает только preview-данные, но интерфейс уже отделён
 * от будущего HTTP-клиента и backend API.
 */
export class ProfileContentFacade {
  public constructor(private readonly portfolioContent: PortfolioContent) {}

  public getProfile() {
    return this.portfolioContent.profile;
  }

  public getEducation() {
    return this.portfolioContent.education;
  }
}

