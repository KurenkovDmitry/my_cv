import { SectionHeading } from "@portfolio/shared-ui";
import type { ProfileHeroViewModel } from "../../types/domain";
import { ProfileHero } from "../organisms/profile-hero";

interface ProfilePageProps {
  localeCode: "ru" | "en";
  heroViewModel: ProfileHeroViewModel;
  onSpeakSummary: () => void;
  onExploreProjects: () => void;
}

/**
 * Страница публичного профиля.
 */
export function ProfilePage({
  localeCode,
  heroViewModel,
  onSpeakSummary,
  onExploreProjects,
}: ProfilePageProps) {
  return (
    <>
      <ProfileHero
        localeCode={localeCode}
        viewModel={heroViewModel}
        onSpeakSummary={onSpeakSummary}
        onExploreProjects={onExploreProjects}
      />
      <section className="info-section">
        <SectionHeading
          eyebrow={localeCode === "ru" ? "Подход" : "Approach"}
          title={
            localeCode === "ru"
              ? "Проектирую платформы, а не просто страницы."
              : "I design platforms, not just pages."
          }
          description={
            localeCode === "ru"
              ? "Каркас уже учитывает импорт контента, локализацию, темы, безопасность админки и будущий backend-контур."
              : "The foundation already accounts for content import, localization, themes, admin security, and the future backend."
          }
        />
      </section>
    </>
  );
}
