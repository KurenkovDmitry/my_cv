import { useEffect, useMemo, useState } from "react";
import type {
  LocaleCode,
  PortfolioContent,
  SkillProof,
} from "@portfolio/shared-types";
import { resolveContentAssetUrl } from "@portfolio/shared-config";
import type { RegionalLocaleCode } from "@portfolio/modules/localization";
import type { ProjectCardViewModel } from "@portfolio/modules/projects";
import type { ProfileHeroViewModel } from "../../types/domain";

interface ProfilePageProps {
  localeCode: LocaleCode;
  regionalLocale: RegionalLocaleCode;
  content: PortfolioContent;
  heroViewModel: ProfileHeroViewModel;
  projects: ProjectCardViewModel[];
  onSpeakSummary: () => void;
  onExploreProjects: () => void;
}

const translate = <Value extends { ru: string; en: string }>(
  value: Value,
  localeCode: LocaleCode,
) => value[localeCode];

/** Полная страница резюме: от hero до опыта, проектов, стека и образования. */
export function ProfilePage({
  localeCode,
  regionalLocale,
  content,
  heroViewModel,
  projects,
  onSpeakSummary,
  onExploreProjects,
}: ProfilePageProps) {
  const [selectedProof, setSelectedProof] = useState<SkillProof | null>(null);
  const isRussian = localeCode === "ru";
  const marketClass = regionalLocale.toLowerCase().replace("-", "_");

  const featuredProjects = useMemo(() => {
    const preferredIds = regionalLocale === "en-US"
      ? ["fillusion", "highload-ozon", "split-app"]
      : regionalLocale === "en-GB"
        ? ["fillusion", "highload-ozon", "flexi-kanban"]
        : ["fillusion", "flexi-kanban", "split-app"];

    return preferredIds
      .map((projectId) => projects.find((project) => project.id === projectId))
      .filter((project): project is ProjectCardViewModel => Boolean(project));
  }, [projects, regionalLocale]);

  useEffect(() => {
    if (!selectedProof) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedProof(null);
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [selectedProof]);

  const statistics = getRegionalStatistics(regionalLocale);

  return (
    <div className={`resume resume--${marketClass}`}>
      <section className="resume-hero" aria-labelledby="profile-name">
        <div className="resume-hero__content">
          <div className="resume-hero__status-row">
            <span className="signal-pill">
              <span className="signal-pill__dot" aria-hidden="true" />
              {isRussian ? "Системный аналитик" : "Technical System Analyst"}
            </span>
            <span className="resume-hero__location">{heroViewModel.location}</span>
          </div>

          <p className="resume-hero__index">Profile / 2026</p>
          <h1 id="profile-name" className="resume-hero__title">{heroViewModel.displayName}</h1>
          <p className="resume-hero__headline">{heroViewModel.headline}</p>
          <p className="resume-hero__summary">{heroViewModel.summary}</p>

          <div className="resume-hero__actions">
            <button className="button button--primary" type="button" onClick={onExploreProjects}>
              {isRussian ? "Смотреть все проекты" : "View all projects"}
              <span aria-hidden="true">↗</span>
            </button>
            <a className="button button--secondary" href={`mailto:${content.profile.contacts?.find((contact) => contact.kind === "email")?.value ?? ""}`}>
              {isRussian ? "Связаться" : "Get in touch"}
            </a>
            <button className="button button--quiet" type="button" onClick={onSpeakSummary}>
              <span aria-hidden="true">◖</span>
              {isRussian ? "Озвучить" : "Listen"}
            </button>
          </div>

          <dl className="resume-hero__stats">
            {statistics.map((statistic) => (
              <div key={statistic.label}>
                <dt>{statistic.label}</dt>
                <dd>{statistic.value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="resume-hero__portrait-wrap">
          <div className="resume-hero__portrait-frame">
            <img className="resume-hero__portrait" src={heroViewModel.avatarAsset} alt={heroViewModel.displayName} />
            <div className="resume-hero__portrait-grid" aria-hidden="true" />
            <div className="resume-hero__portrait-caption">
              <span>Highload</span>
              <span>Systems</span>
              <span>Data</span>
            </div>
          </div>
          {content.profile.availability ? (
            <p className="resume-hero__availability">
              <span aria-hidden="true">↳</span>
              {translate(content.profile.availability, localeCode)}
            </p>
          ) : null}
        </div>
      </section>

      <section className="contact-strip" aria-label={isRussian ? "Контакты" : "Contacts"}>
        {(content.profile.contacts ?? []).map((contact) => (
          <a className="contact-strip__item" href={contact.href} key={`${contact.kind}-${contact.value}`} target={contact.href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
            <span>{contact.label}</span>
            <strong>{contact.value}</strong>
          </a>
        ))}
      </section>

      <section className="resume-section" id="experience">
        <SectionIntro
          index="01"
          eyebrow={isRussian ? "Опыт" : "Experience"}
          title={isRussian ? "Работа на стыке анализа и реализации." : "Analysis grounded in implementation."}
          description={isRussian
            ? "Роли и задачи приведены полностью по резюме - без маркетингового пересказа."
            : "Roles and scope are retained from the source CV, with implementation context kept intact."}
        />
        <div className="timeline">
          {content.experience.map((experience, index) => (
            <article className="timeline__item" key={experience.id}>
              <div className="timeline__rail" aria-hidden="true">
                <span>{String(index + 1).padStart(2, "0")}</span>
              </div>
              <div className="timeline__content">
                <header className="timeline__header">
                  <div>
                    <p className="timeline__period">{experience.period ? translate(experience.period, localeCode) : ""}</p>
                    <h3>{translate(experience.company, localeCode)}</h3>
                  </div>
                  <p className="timeline__role">{translate(experience.role, localeCode)}</p>
                </header>
                {experience.description ? <p className="timeline__description">{translate(experience.description, localeCode)}</p> : null}
                {experience.highlights?.length ? (
                  <ul className="detail-list">
                    {experience.highlights.map((highlight) => (
                      <li key={highlight.ru}>{translate(highlight, localeCode)}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="resume-section" id="projects">
        <SectionIntro
          index="02"
          eyebrow={isRussian ? "Избранные проекты" : "Selected work"}
          title={isRussian ? "От микросервисов до продуктовых досок." : "From microservices to product workflows."}
          description={isRussian
            ? "На главной - три акцента для выбранного рынка. Полная история из семи проектов открывается отдельно."
            : "The overview prioritises three market-relevant cases; the full seven-project history remains one click away."}
          actionLabel={isRussian ? "Все 7 проектов" : "All 7 projects"}
          onAction={onExploreProjects}
        />
        <div className="featured-projects">
          {featuredProjects.map((project, index) => (
            <article className="featured-project" key={project.id}>
              <header>
                <span className="featured-project__number">0{index + 1}</span>
                <span className="featured-project__period">{project.period}</span>
              </header>
              <h3>{project.title}</h3>
              <p className="featured-project__role">{project.role}</p>
              <p>{project.summary}</p>
              {project.achievements[0] ? <strong className="featured-project__impact">{project.achievements[0]}</strong> : null}
              <ul className="chip-list">
                {project.technologies.slice(0, 5).map((technology) => <li key={technology}>{technology}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="resume-section" id="skills">
        <SectionIntro
          index="03"
          eyebrow={isRussian ? "Навыки" : "Capabilities"}
          title={isRussian ? "Стек сгруппирован по задачам, а не по моде." : "A task-shaped stack, not a trend list."}
          description={content.skills.proofNote ? translate(content.skills.proofNote, localeCode) : undefined}
        />
        <div className="skills-grid">
          {(content.skills.groups ?? []).map((group) => (
            <article className="skill-group" key={group.id}>
              <div className="skill-group__index">{group.id.slice(0, 2).toUpperCase()}</div>
              <h3>{translate(group.title, localeCode)}</h3>
              <ul className="skill-group__items">
                {group.items.map((skill) => {
                  const skillLabel = typeof skill === "string" ? skill : translate(skill, localeCode);
                  const proof = content.skills.proofs?.find((item) => item.skill === skillLabel);
                  return (
                    <li key={skillLabel}>
                      <span>{skillLabel}</span>
                      {proof ? (
                        <button type="button" onClick={() => setSelectedProof(proof)} aria-label={`${skillLabel}: ${isRussian ? "открыть подтверждение" : "open evidence"}`}>
                          {isRussian ? "подтверждено" : "evidence"}
                        </button>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="resume-section" id="education">
        <SectionIntro
          index="04"
          eyebrow={isRussian ? "Образование" : "Education"}
          title={isRussian ? "Фундамент и прикладная инженерия." : "Academic foundation, applied engineering."}
        />
        <div className="education-list">
          {content.education.map((education, index) => {
            const educationProof = content.skills.proofs?.find((proof) => proof.id === education.proofId);
            return (
              <article className="education-card" key={education.id}>
                <span className="education-card__year">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <p>{education.period ? translate(education.period, localeCode) : ""}</p>
                  <h3>{translate(education.title, localeCode)}</h3>
                  {education.programme ? <span>{translate(education.programme, localeCode)}</span> : null}
                </div>
                <div className="education-card__evidence">
                  {education.detail ? <strong>{translate(education.detail, localeCode)}</strong> : null}
                  {educationProof ? (
                    <button type="button" onClick={() => setSelectedProof(educationProof)}>
                      {isRussian ? "Открыть диплом" : "View diploma"} <span aria-hidden="true">↗</span>
                    </button>
                  ) : education.assetId ? (
                    <a href={resolveContentAssetUrl(education.assetId, "")} target="_blank" rel="noreferrer">
                      {isRussian ? "Открыть документ" : "View document"} <span aria-hidden="true">↗</span>
                    </a>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="resume-contact" id="contact">
        <p className="resume-contact__eyebrow">05 / Contact</p>
        <h2>{isRussian ? "Обсудим систему, которую нужно разобрать или спроектировать." : "Let’s discuss the system you need to understand or design."}</h2>
        <div className="resume-contact__actions">
          <a className="button button--primary" href="mailto:dimakurenkov33557080@gmail.com">dimakurenkov33557080@gmail.com</a>
          <a className="button button--secondary" href="https://t.me/KURDMIALE" target="_blank" rel="noreferrer">Telegram ↗</a>
        </div>
      </section>

      {selectedProof ? (
        <ProofModal proof={selectedProof} localeCode={localeCode} onClose={() => setSelectedProof(null)} />
      ) : null}
    </div>
  );
}

interface SectionIntroProps {
  index: string;
  eyebrow: string;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

function SectionIntro({ index, eyebrow, title, description, actionLabel, onAction }: SectionIntroProps) {
  return (
    <header className="section-intro">
      <div className="section-intro__marker"><span>{index}</span><span>{eyebrow}</span></div>
      <div className="section-intro__copy">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {actionLabel && onAction ? <button type="button" onClick={onAction}>{actionLabel} <span aria-hidden="true">→</span></button> : null}
    </header>
  );
}

function ProofModal({ proof, localeCode, onClose }: { proof: SkillProof; localeCode: LocaleCode; onClose: () => void }) {
  const isRussian = localeCode === "ru";
  return (
    <div className="proof-modal" role="presentation" onMouseDown={onClose}>
      <article className="proof-modal__card" role="dialog" aria-modal="true" aria-labelledby="proof-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="icon-button proof-modal__close" type="button" onClick={onClose} aria-label={isRussian ? "Закрыть" : "Close"}>×</button>
        <div className="proof-modal__seal" aria-hidden="true"><span>✓</span></div>
        <p className="proof-modal__eyebrow">{isRussian ? "Подтверждение компетенции" : "Capability evidence"}</p>
        <h2 id="proof-title">{translate(proof.title, localeCode)}</h2>
        {proof.level ? <p className="proof-modal__level">{translate(proof.level, localeCode)}</p> : null}
        {proof.issuer ? <p className="proof-modal__issuer">{translate(proof.issuer, localeCode)}</p> : null}
        {proof.validUntil ? (
          <p className="proof-modal__validity">
            {isRussian ? "Действителен до" : "Valid until"}: {formatProofDate(proof.validUntil, localeCode)}
          </p>
        ) : null}
        {proof.note ? <p className="proof-modal__note">{translate(proof.note, localeCode)}</p> : null}
        {proof.assetId || proof.assetHref ? <a className="button button--primary" href={resolveContentAssetUrl(proof.assetId, proof.assetHref ?? "")} target="_blank" rel="noreferrer">{isRussian ? "Открыть документ" : "Open document"}</a> : <span className="proof-modal__status">{isRussian ? "Оригинал предоставляется по запросу" : "Original available on request"}</span>}
      </article>
    </div>
  );
}

/** Форматирует ISO-дату подтверждения без зависимости от локали браузера. */
function formatProofDate(isoDate: string, localeCode: LocaleCode): string {
  return new Intl.DateTimeFormat(localeCode === "ru" ? "ru-RU" : "en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T00:00:00Z`));
}

function getRegionalStatistics(localeCode: RegionalLocaleCode) {
  if (localeCode === "ru") {
    return [
      { value: "7", label: "проектов в резюме" },
      { value: "5", label: "сертификатов навыков" },
      { value: "продвинутый", label: "API-компетенция" },
    ];
  }

  if (localeCode === "en-US") {
    return [
      { value: "Advanced", label: "API competency" },
      { value: "5", label: "skill certificates" },
      { value: "7", label: "portfolio projects" },
    ];
  }

  return [
      { value: "7", label: "documented projects" },
      { value: "5", label: "skill certificates" },
      { value: "Honours", label: "Bauman degree" },
  ];
}
