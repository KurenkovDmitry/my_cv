import type { ProfileHeroViewModel } from "../../types/domain";

interface ProfileHeroProps {
  viewModel: ProfileHeroViewModel;
  onSpeakSummary: () => void;
  onExploreProjects: () => void;
  localeCode: "ru" | "en";
}

/**
 * Главный hero-блок публичной страницы.
 */
export function ProfileHero({
  viewModel,
  onSpeakSummary,
  onExploreProjects,
  localeCode,
}: ProfileHeroProps) {
  const speakLabel = localeCode === "ru" ? "Озвучить вступление" : "Read intro aloud";

  return (
    <section className="profile-hero">
      <div className="profile-hero__copy">
        <p className="profile-hero__eyebrow">Highload • Infrastructure • Product UI</p>
        <h1 className="profile-hero__title">{viewModel.displayName}</h1>
        <p className="profile-hero__headline">{viewModel.headline}</p>
        <p className="profile-hero__summary">{viewModel.summary}</p>
        <div className="profile-hero__actions">
          <button className="profile-hero__primary-action" type="button" onClick={onExploreProjects}>
            {localeCode === "ru" ? "Открыть проекты" : "Explore projects"}
          </button>
          <button
            className="profile-hero__secondary-action"
            type="button"
            onClick={onSpeakSummary}
          >
            {speakLabel}
          </button>
        </div>
        <ul className="profile-hero__badges" aria-label="Education">
          {viewModel.educationBadges.map((badge) => (
            <li key={badge} className="profile-hero__badge">
              {badge}
            </li>
          ))}
        </ul>
      </div>
      <div className="profile-hero__visual">
        <div className="profile-hero__portrait-card">
          <img className="profile-hero__portrait" src={viewModel.avatarAsset} alt={viewModel.displayName} />
          <p className="profile-hero__location">{viewModel.location}</p>
        </div>
      </div>
    </section>
  );
}
