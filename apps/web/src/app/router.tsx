import { Route, Routes } from "react-router-dom";
import { ProfilePage } from "@portfolio/modules/profile";
import { ProjectsPage } from "@portfolio/modules/projects";
import type { ProfileHeroViewModel } from "@portfolio/modules/profile";
import type { ProjectCardViewModel } from "@portfolio/modules/projects";
import type { LocaleCode, PortfolioContent } from "@portfolio/shared-types";
import type { RegionalLocaleCode } from "@portfolio/modules/localization";

interface AppRouterProps {
  localeCode: LocaleCode;
  regionalLocale: RegionalLocaleCode;
  content: PortfolioContent;
  heroViewModel: ProfileHeroViewModel;
  projectCards: ProjectCardViewModel[];
  onSpeakSummary: () => void;
  onExploreProjects: () => void;
}

/**
 * Маршруты публичного SPA.
 */
export function AppRouter({
  localeCode,
  regionalLocale,
  content,
  heroViewModel,
  projectCards,
  onSpeakSummary,
  onExploreProjects,
}: AppRouterProps) {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProfilePage
            localeCode={localeCode}
            regionalLocale={regionalLocale}
            content={content}
            heroViewModel={heroViewModel}
            projects={projectCards}
            onSpeakSummary={onSpeakSummary}
            onExploreProjects={onExploreProjects}
          />
        }
      />
      <Route
        path="/projects"
        element={<ProjectsPage regionalLocale={regionalLocale} projects={projectCards} />}
      />
    </Routes>
  );
}
