import { Route, Routes } from "react-router-dom";
import { ProfilePage } from "@portfolio/modules/profile";
import { ProjectsPage } from "@portfolio/modules/projects";
import type { ProfileHeroViewModel } from "@portfolio/modules/profile";
import type { ProjectCardViewModel } from "@portfolio/modules/projects";

interface AppRouterProps {
  localeCode: "ru" | "en";
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
            heroViewModel={heroViewModel}
            onSpeakSummary={onSpeakSummary}
            onExploreProjects={onExploreProjects}
          />
        }
      />
      <Route
        path="/projects"
        element={<ProjectsPage localeCode={localeCode} projects={projectCards} />}
      />
    </Routes>
  );
}
