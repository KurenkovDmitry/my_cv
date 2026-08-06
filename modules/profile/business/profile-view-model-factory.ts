import type { LocaleCode } from "@portfolio/shared-types";
import { resolveContentAssetUrl } from "@portfolio/shared-config";
import { LocaleService } from "@portfolio/modules/localization";
import { ProfileContentFacade } from "../api/profile-content-facade";
import type { ProfileHeroViewModel } from "../types/domain";

/**
 * Фабрика view model для hero-блока профиля.
 */
export class ProfileViewModelFactory {
  public constructor(
    private readonly localeService: LocaleService,
    private readonly profileContentFacade: ProfileContentFacade,
  ) {}

  public createHeroViewModel(localeCode: LocaleCode): ProfileHeroViewModel {
    const profile = this.profileContentFacade.getProfile();
    const education = this.profileContentFacade.getEducation();

    return {
      displayName: this.localeService.translate(profile.displayName, localeCode),
      headline: this.localeService.translate(profile.headline, localeCode),
      summary: this.localeService.translate(profile.summary, localeCode),
      location: this.localeService.translate(profile.location, localeCode),
      avatarAsset: resolveContentAssetUrl(profile.avatarAssetId, profile.avatarAsset),
      educationBadges: education.map((educationItem) =>
        this.localeService.translate(educationItem.title, localeCode),
      ),
    };
  }
}
