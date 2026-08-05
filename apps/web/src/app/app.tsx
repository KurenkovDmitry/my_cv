import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { frontendEnvConfig, portfolioPreviewContent } from "@portfolio/shared-config";
import { PageShell } from "@portfolio/shared-ui";
import {
  AnalyticsEventFacade,
  AnalyticsService,
  type RouteAnalyticsDescriptor,
} from "@portfolio/modules/analytics";
import { ConsentModal, ConsentService, ConsentStorageFacade } from "@portfolio/modules/consent";
import {
  LocaleService,
  LocaleStorageFacade,
  LocaleSwitcher,
  type RegionalLocaleCode,
} from "@portfolio/modules/localization";
import { ProfileContentFacade, ProfileViewModelFactory } from "@portfolio/modules/profile";
import {
  ProjectBusinessService,
  ProjectContentFacade,
  ProjectViewModelFactory,
} from "@portfolio/modules/projects";
import { ThemeStorageFacade } from "@portfolio/modules/themes";
import type { ConsentStateSnapshot, LocaleCode, PortfolioContent } from "@portfolio/shared-types";
import { fetchPublicPortfolio } from "./public-portfolio-http-client";
import { AppRouter } from "./router";
import {
  SettingsPanel,
  type ColorPreference,
  type VisualPreferences,
} from "./settings-panel";

const localeStorageFacade = new LocaleStorageFacade();
const themeStorageFacade = new ThemeStorageFacade();
const consentStorageFacade = new ConsentStorageFacade();
const consentService = new ConsentService();
const analyticsService = new AnalyticsService(
  new AnalyticsEventFacade(frontendEnvConfig.publicApiBaseUrl),
);

const VISUAL_PREFERENCES_KEY = "portfolio.visual-preferences.v2";
const KNOWN_THEMES = ["engineering-blueprint", "papyrus-scroll"];

function resolveRouteAnalytics(pathname: string): RouteAnalyticsDescriptor {
  return pathname === "/projects"
    ? { routeKey: "projects", sectionKeys: ["projects_grid"] }
    : { routeKey: "home", sectionKeys: ["hero", "experience", "projects", "skills", "education"] };
}

function resolveRegionalLocale(): RegionalLocaleCode {
  const persistedLocale = localeStorageFacade.readPreferredLocale();
  if (persistedLocale) {
    return persistedLocale;
  }

  const browserLocale = navigator.language.toLowerCase();
  if (browserLocale.startsWith("ru")) {
    return "ru";
  }

  return browserLocale === "en-us" ? "en-US" : "en-GB";
}

function readVisualPreferences(): VisualPreferences {
  const fallback: VisualPreferences = {
    colorPreference: "system",
    ambientLight: false,
    pointerEdges: true,
    scrollUnroll: true,
  };

  try {
    const stored = window.localStorage.getItem(VISUAL_PREFERENCES_KEY);
    if (!stored) {
      return fallback;
    }

    const candidate = JSON.parse(stored) as Partial<VisualPreferences>;
    const colorPreference: ColorPreference = ["system", "light", "dark"].includes(candidate.colorPreference ?? "")
      ? candidate.colorPreference as ColorPreference
      : fallback.colorPreference;

    return {
      colorPreference,
      ambientLight: candidate.ambientLight ?? fallback.ambientLight,
      pointerEdges: candidate.pointerEdges ?? fallback.pointerEdges,
      scrollUnroll: candidate.scrollUnroll ?? fallback.scrollUnroll,
    };
  } catch {
    return fallback;
  }
}

/**
 * Live API может отдать snapshot предыдущей версии. Детальные поля из preview дополняют его,
 * а опубликованные значения по-прежнему имеют приоритет.
 */
function enrichPortfolioContent(liveContent: PortfolioContent): PortfolioContent {
  const mergeById = <Item extends { id: string }>(fallbackItems: Item[], liveItems: Item[]) => {
    const liveMap = new Map(liveItems.map((item) => [item.id, item]));
    const merged = fallbackItems.map((fallbackItem) => ({
      ...fallbackItem,
      ...(liveMap.get(fallbackItem.id) ?? {}),
    }));
    const fallbackIds = new Set(fallbackItems.map((item) => item.id));
    return [...merged, ...liveItems.filter((item) => !fallbackIds.has(item.id))];
  };

  return {
    ...portfolioPreviewContent,
    ...liveContent,
    profile: {
      ...portfolioPreviewContent.profile,
      ...liveContent.profile,
      contacts: liveContent.profile.contacts ?? portfolioPreviewContent.profile.contacts,
      availability: liveContent.profile.availability ?? portfolioPreviewContent.profile.availability,
    },
    education: mergeById(portfolioPreviewContent.education, liveContent.education),
    experience: mergeById(portfolioPreviewContent.experience, liveContent.experience),
    projects: mergeById(portfolioPreviewContent.projects, liveContent.projects),
    skills: {
      ...portfolioPreviewContent.skills,
      ...liveContent.skills,
      groups: liveContent.skills.groups ?? portfolioPreviewContent.skills.groups,
      proofs: liveContent.skills.proofs ?? portfolioPreviewContent.skills.proofs,
      proofNote: liveContent.skills.proofNote ?? portfolioPreviewContent.skills.proofNote,
    },
  };
}

export function App() {
  return (
    <BrowserRouter>
      <RoutedApp />
    </BrowserRouter>
  );
}

function RoutedApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const [portfolioContent, setPortfolioContent] = useState<PortfolioContent>(portfolioPreviewContent);
  const [regionalLocale, setRegionalLocale] = useState<RegionalLocaleCode>(resolveRegionalLocale);
  const [themeId, setThemeId] = useState(() => {
    const storedTheme = themeStorageFacade.readPreferredTheme();
    return storedTheme && KNOWN_THEMES.includes(storedTheme) ? storedTheme : "engineering-blueprint";
  });
  const [preferences, setPreferences] = useState<VisualPreferences>(readVisualPreferences);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [consentState, setConsentState] = useState<ConsentStateSnapshot | null>(() => consentStorageFacade.readConsentState());
  const sessionBootstrappedRef = useRef(false);

  const localeCode: LocaleCode = regionalLocale === "ru" ? "ru" : "en";
  const localeService = useMemo(
    () => new LocaleService(
      portfolioContent.localization.supportedLocales,
      portfolioContent.localization.defaultLocale,
      portfolioContent.localization.autoDetectByRegion,
    ),
    [portfolioContent.localization],
  );
  const profileViewModelFactory = useMemo(
    () => new ProfileViewModelFactory(localeService, new ProfileContentFacade(portfolioContent)),
    [localeService, portfolioContent],
  );
  const projectBusinessService = useMemo(
    () => new ProjectBusinessService(
      new ProjectContentFacade(portfolioContent),
      new ProjectViewModelFactory(localeService),
    ),
    [localeService, portfolioContent],
  );
  const heroViewModel = useMemo(
    () => profileViewModelFactory.createHeroViewModel(localeCode),
    [localeCode, profileViewModelFactory],
  );
  const projectCards = useMemo(
    () => projectBusinessService.getAllProjectCards(localeCode),
    [localeCode, projectBusinessService],
  );

  const consentContent = portfolioContent.legal.analyticsConsent;
  const activeRoute = useMemo(() => resolveRouteAnalytics(location.pathname), [location.pathname]);
  const shouldPromptConsent = consentService.shouldRequestConsent(consentContent, consentState);
  const isConsentAccepted = consentService.isAcceptedCurrentVersion(consentContent, consentState);
  const isConsentRejected = consentService.isRejectedCurrentVersion(consentContent, consentState);

  useEffect(() => {
    const abortController = new AbortController();

    void fetchPublicPortfolio(abortController.signal)
      .then((response) => setPortfolioContent(enrichPortfolioContent(response.payload)))
      .catch((error: unknown) => {
        if (!abortController.signal.aborted && import.meta.env.DEV) {
          console.info("Portfolio API unavailable; using the complete preview snapshot.", error);
        }
      });

    return () => abortController.abort();
  }, []);

  useEffect(() => {
    localeStorageFacade.persistPreferredLocale(regionalLocale);
    document.documentElement.lang = regionalLocale;
    document.documentElement.dataset.region = regionalLocale.toLowerCase();
    document.title = localeCode === "ru"
      ? "Дмитрий Куренков — системный аналитик"
      : "Dmitry Kurenkov — Technical System Analyst";
  }, [regionalLocale]);

  useEffect(() => {
    themeStorageFacade.persistPreferredTheme(themeId);
    document.documentElement.dataset.theme = themeId;
  }, [themeId]);

  useEffect(() => {
    window.localStorage.setItem(VISUAL_PREFERENCES_KEY, JSON.stringify(preferences));
    document.documentElement.dataset.ambient = String(preferences.ambientLight);
    document.documentElement.dataset.pointerEdges = String(preferences.pointerEdges);
    document.documentElement.dataset.scrollUnroll = String(preferences.scrollUnroll);
  }, [preferences]);

  useEffect(() => {
    const colorMedia = window.matchMedia("(prefers-color-scheme: dark)");
    const applyColorMode = () => {
      const resolvedMode = preferences.colorPreference === "system"
        ? colorMedia.matches ? "dark" : "light"
        : preferences.colorPreference;
      document.documentElement.dataset.colorMode = resolvedMode;
      document.documentElement.dataset.colorPreference = preferences.colorPreference;
    };

    applyColorMode();
    colorMedia.addEventListener("change", applyColorMode);
    return () => colorMedia.removeEventListener("change", applyColorMode);
  }, [preferences.colorPreference]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const normalizedX = event.clientX / window.innerWidth;
      const normalizedY = event.clientY / window.innerHeight;
      document.documentElement.style.setProperty("--cursor-x", normalizedX.toFixed(3));
      document.documentElement.style.setProperty("--cursor-y", normalizedY.toFixed(3));
      document.documentElement.style.setProperty("--edge-x", ((normalizedX - 0.5) * 2).toFixed(3));
      document.documentElement.style.setProperty("--edge-y", ((normalizedY - 0.5) * 2).toFixed(3));
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    return () => window.removeEventListener("pointermove", handlePointerMove);
  }, []);

  useEffect(() => {
    let frameId = 0;
    const updateScrollProgress = () => {
      const scrollRange = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1);
      const progress = Math.min(Math.max(window.scrollY / scrollRange, 0), 1);
      document.documentElement.style.setProperty("--scroll-progress", progress.toFixed(4));
      frameId = 0;
    };
    const handleScroll = () => {
      if (!frameId) {
        frameId = window.requestAnimationFrame(updateScrollProgress);
      }
    };

    updateScrollProgress();
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
      if (frameId) window.cancelAnimationFrame(frameId);
    };
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);

  useEffect(() => {
    if (!isConsentAccepted || sessionBootstrappedRef.current || !consentState) {
      return;
    }
    sessionBootstrappedRef.current = true;
    void analyticsService.bootstrapAcceptedSession(activeRoute.routeKey, localeCode, consentState.storageMode);
  }, [activeRoute.routeKey, consentState, isConsentAccepted, localeCode]);

  useEffect(() => {
    if (isConsentAccepted) {
      void analyticsService.trackRouteSections(activeRoute.routeKey, localeCode, activeRoute.sectionKeys);
    }
  }, [activeRoute, isConsentAccepted, localeCode]);

  useEffect(() => {
    if (!isConsentRejected) {
      return;
    }
    const closeTimeoutId = window.setTimeout(() => window.location.replace("about:blank"), 160);
    return () => window.clearTimeout(closeTimeoutId);
  }, [isConsentRejected]);

  const handleThemeChange = useCallback((nextThemeId: string) => {
    if (KNOWN_THEMES.includes(nextThemeId)) {
      analyticsService.trackActionClick(activeRoute.routeKey, "settings", "switch_theme", localeCode);
      setThemeId(nextThemeId);
    }
  }, [activeRoute.routeKey, localeCode]);

  const handleLocaleChange = (nextLocale: RegionalLocaleCode) => {
    analyticsService.trackActionClick(activeRoute.routeKey, "topbar", "switch_locale", localeCode);
    setRegionalLocale(nextLocale);
  };

  const handleExploreProjects = () => {
    analyticsService.trackActionClick(activeRoute.routeKey, "hero", "open_projects", localeCode);
    navigate("/projects");
  };

  const speakSummary = () => {
    analyticsService.trackActionClick(activeRoute.routeKey, "hero", "read_intro", localeCode);
    if (!portfolioContent.accessibility.speechSynthesisEnabled || !("speechSynthesis" in window)) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(heroViewModel.summary);
    utterance.lang = regionalLocale;
    window.speechSynthesis.speak(utterance);
  };

  if (isConsentRejected) {
    return (
      <div className="site-blocked">
        <div className="site-blocked__card">
          <p className="site-blocked__eyebrow">{localeCode === "ru" ? "Доступ остановлен" : "Access stopped"}</p>
          <h1>{localeCode === "ru" ? "Страница закрыта после отказа от аналитики." : "The page was closed after analytics consent was declined."}</h1>
        </div>
      </div>
    );
  }

  const localeOptions = [
    { code: "ru" as const, label: "RU" },
    { code: "en-GB" as const, label: "UK" },
    { code: "en-US" as const, label: "US" },
  ];
  const isRussian = localeCode === "ru";

  return (
    <>
      <div className="app-background" aria-hidden="true">
        <div className="app-background__grid" />
        <div className="app-background__topology" />
        <div className="app-background__light" />
      </div>

      <div className="portfolio-stage">
        <div className="papyrus-edge papyrus-edge--left" aria-hidden="true" />
        <div className="papyrus-edge papyrus-edge--right" aria-hidden="true" />
        <div className="papyrus-roller papyrus-roller--top" aria-hidden="true"><span /></div>
        <div className="papyrus-roller papyrus-roller--bottom" aria-hidden="true"><span /></div>

        <PageShell>
          <header className="topbar">
            <Link className="brandmark" to="/" aria-label={portfolioContent.seo.siteName[localeCode]}>
              <span className="brandmark__monogram">DK</span>
              <span className="brandmark__copy">
                <strong>{isRussian ? "Дмитрий Куренков" : "Dmitry Kurenkov"}</strong>
                <small>System Analysis / Architecture</small>
              </span>
            </Link>

            <nav className="topbar__nav" aria-label={isRussian ? "Основная навигация" : "Main navigation"}>
              <NavLink className="topbar__link" to="/">{isRussian ? "Профиль" : "Profile"}</NavLink>
              <a className="topbar__link" href="/#experience">{isRussian ? "Опыт" : "Experience"}</a>
              <NavLink className="topbar__link" to="/projects">{isRussian ? "Проекты" : "Projects"}</NavLink>
              <a className="topbar__link" href="/#contact">{isRussian ? "Контакты" : "Contact"}</a>
            </nav>

            <div className="topbar__controls">
              <LocaleSwitcher
                currentLocale={regionalLocale}
                availableLocales={localeOptions}
                onLocaleChange={handleLocaleChange}
              />
              <button className="settings-button" type="button" onClick={() => setSettingsOpen(true)}>
                <span className="settings-button__icon" aria-hidden="true">⌘</span>
                <span>{isRussian ? "Вид" : "View"}</span>
              </button>
            </div>
          </header>

          <main className="main-content">
            <AppRouter
              localeCode={localeCode}
              regionalLocale={regionalLocale}
              content={portfolioContent}
              heroViewModel={heroViewModel}
              projectCards={projectCards}
              onSpeakSummary={speakSummary}
              onExploreProjects={handleExploreProjects}
            />
          </main>

          <footer className="site-footer">
            <span>© 2026 {isRussian ? "Дмитрий Куренков" : "Dmitry Kurenkov"}</span>
            <span>System analysis · Highload · Data</span>
            <a href="#root">{isRussian ? "Наверх ↑" : "Back to top ↑"}</a>
          </footer>
        </PageShell>
      </div>

      <SettingsPanel
        open={settingsOpen}
        localeCode={regionalLocale}
        themeId={themeId}
        preferences={preferences}
        onClose={() => setSettingsOpen(false)}
        onThemeChange={handleThemeChange}
        onPreferencesChange={setPreferences}
      />

      {shouldPromptConsent ? (
        <ConsentModal
          localeCode={localeCode}
          content={consentContent}
          onAccept={() => setConsentState(consentStorageFacade.persistAccepted(consentContent.version))}
          onReject={() => setConsentState(consentStorageFacade.persistRejected(consentContent.version))}
        />
      ) : null}
    </>
  );
}
