import { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { frontendEnvConfig, portfolioPreviewContent } from "@portfolio/shared-config";
import { PageShell } from "@portfolio/shared-ui";
import {
  AnalyticsEventFacade,
  AnalyticsService,
  type RouteAnalyticsDescriptor,
} from "@portfolio/modules/analytics";
import {
  ConsentModal,
  ConsentService,
  ConsentStorageFacade,
} from "@portfolio/modules/consent";
import {
  LocaleService,
  LocaleStorageFacade,
  LocaleSwitcher,
} from "@portfolio/modules/localization";
import { ProfileContentFacade, ProfileViewModelFactory } from "@portfolio/modules/profile";
import {
  ProjectBusinessService,
  ProjectContentFacade,
  ProjectViewModelFactory,
} from "@portfolio/modules/projects";
import { ThemeService, ThemeStorageFacade, ThemeSwitcher } from "@portfolio/modules/themes";
import type { PortfolioContent, ConsentStateSnapshot, LocaleCode } from "@portfolio/shared-types";
import { fetchPublicPortfolio } from "./public-portfolio-http-client";
import { AppRouter } from "./router";

const localeStorageFacade = new LocaleStorageFacade();
const themeStorageFacade = new ThemeStorageFacade();
const consentStorageFacade = new ConsentStorageFacade();
const consentService = new ConsentService();
const analyticsService = new AnalyticsService(
  new AnalyticsEventFacade(frontendEnvConfig.publicApiBaseUrl),
);

type ContentSourceKind = "live_api" | "preview_fallback";

function resolveRouteAnalytics(pathname: string): RouteAnalyticsDescriptor {
  if (pathname === "/projects") {
    return {
      routeKey: "projects",
      sectionKeys: ["projects_grid"],
    };
  }

  return {
    routeKey: "home",
    sectionKeys: ["hero", "profile_summary"],
  };
}

/**
 * Корневой компонент публичного frontend-приложения.
 */
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
  const [contentSource, setContentSource] = useState<ContentSourceKind>("preview_fallback");
  const [portfolioLoadError, setPortfolioLoadError] = useState<string | null>(null);
  const [localeCode, setLocaleCode] = useState<LocaleCode>(() => {
    const bootstrapLocaleService = new LocaleService(
      portfolioPreviewContent.localization.supportedLocales,
      portfolioPreviewContent.localization.defaultLocale,
      portfolioPreviewContent.localization.autoDetectByRegion,
    );
    const persistedLocale = localeStorageFacade.readPreferredLocale();

    if (persistedLocale) {
      return persistedLocale;
    }

    return bootstrapLocaleService.resolveInitialLocale(navigator.language, "RU");
  });
  const [themeId, setThemeId] = useState(() => {
    const bootstrapThemeService = new ThemeService(
      portfolioPreviewContent.themes.available,
      portfolioPreviewContent.themes.active,
    );
    return bootstrapThemeService.resolveInitialTheme(themeStorageFacade.readPreferredTheme());
  });
  const [consentState, setConsentState] = useState<ConsentStateSnapshot | null>(() =>
    consentStorageFacade.readConsentState(),
  );
  const sessionBootstrappedRef = useRef(false);

  const localeService = useMemo(
    () =>
      new LocaleService(
        portfolioContent.localization.supportedLocales,
        portfolioContent.localization.defaultLocale,
        portfolioContent.localization.autoDetectByRegion,
      ),
    [portfolioContent.localization],
  );
  const themeService = useMemo(
    () => new ThemeService(portfolioContent.themes.available, portfolioContent.themes.active),
    [portfolioContent.themes],
  );
  const profileViewModelFactory = useMemo(
    () => new ProfileViewModelFactory(localeService, new ProfileContentFacade(portfolioContent)),
    [localeService, portfolioContent],
  );
  const projectBusinessService = useMemo(
    () =>
      new ProjectBusinessService(
        new ProjectContentFacade(portfolioContent),
        new ProjectViewModelFactory(localeService),
      ),
    [localeService, portfolioContent],
  );

  const consentContent = portfolioContent.legal.analyticsConsent;
  const activeRoute = useMemo(() => resolveRouteAnalytics(location.pathname), [location.pathname]);
  const shouldPromptConsent = consentService.shouldRequestConsent(consentContent, consentState);
  const isConsentAccepted = consentService.isAcceptedCurrentVersion(consentContent, consentState);
  const isConsentRejected = consentService.isRejectedCurrentVersion(consentContent, consentState);

  const heroViewModel = useMemo(
    () => profileViewModelFactory.createHeroViewModel(localeCode),
    [localeCode, profileViewModelFactory],
  );
  const projectCards = useMemo(
    () => projectBusinessService.getFeaturedProjectCards(localeCode),
    [localeCode, projectBusinessService],
  );

  useEffect(() => {
    const abortController = new AbortController();

    void (async () => {
      try {
        const portfolioResponse = await fetchPublicPortfolio(abortController.signal);
        setPortfolioContent(portfolioResponse.payload);
        setContentSource("live_api");
        setPortfolioLoadError(null);
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }

        setContentSource("preview_fallback");
        setPortfolioLoadError(error instanceof Error ? error.message : "Unknown portfolio loading error.");
      }
    })();

    return () => abortController.abort();
  }, []);

  useEffect(() => {
    localeStorageFacade.persistPreferredLocale(localeCode);
  }, [localeCode]);

  useEffect(() => {
    const supportedLocales = portfolioContent.localization.supportedLocales;

    if (!supportedLocales.includes(localeCode)) {
      setLocaleCode(portfolioContent.localization.defaultLocale);
    }
  }, [localeCode, portfolioContent.localization.defaultLocale, portfolioContent.localization.supportedLocales]);

  useEffect(() => {
    if (!portfolioContent.themes.available.some((themeOption) => themeOption.id === themeId)) {
      setThemeId(themeService.resolveInitialTheme(themeStorageFacade.readPreferredTheme()));
    }
  }, [portfolioContent.themes.available, themeId, themeService]);

  useEffect(() => {
    themeStorageFacade.persistPreferredTheme(themeId);
    themeService.applyTheme(themeId);
  }, [themeId, themeService]);

  useEffect(() => {
    if (!frontendEnvConfig.enableDynamicBackdrop) {
      return;
    }

    const handlePointerMove = (event: PointerEvent) => {
      const normalizedX = (event.clientX / window.innerWidth).toFixed(3);
      const normalizedY = (event.clientY / window.innerHeight).toFixed(3);
      document.documentElement.style.setProperty("--cursor-x", normalizedX);
      document.documentElement.style.setProperty("--cursor-y", normalizedY);
    };

    window.addEventListener("pointermove", handlePointerMove);
    return () => window.removeEventListener("pointermove", handlePointerMove);
  }, []);

  useEffect(() => {
    if (!isConsentAccepted || sessionBootstrappedRef.current || !consentState) {
      return;
    }

    sessionBootstrappedRef.current = true;
    void analyticsService.bootstrapAcceptedSession(
      activeRoute.routeKey,
      localeCode,
      consentState.storageMode,
    );
  }, [activeRoute.routeKey, consentState, isConsentAccepted, localeCode]);

  useEffect(() => {
    if (!isConsentAccepted) {
      return;
    }

    void analyticsService.trackRouteSections(
      activeRoute.routeKey,
      localeCode,
      activeRoute.sectionKeys,
    );
  }, [activeRoute, isConsentAccepted, localeCode]);

  useEffect(() => {
    if (!isConsentRejected) {
      return;
    }

    const closeTimeoutId = window.setTimeout(() => {
      try {
        window.location.replace("about:blank");
      } catch {
        // Если браузер не дал уйти на about:blank, ниже останется жесткая блокирующая заглушка.
      }
    }, 160);

    return () => window.clearTimeout(closeTimeoutId);
  }, [isConsentRejected]);

  const handleAcceptConsent = () => {
    setConsentState(consentStorageFacade.persistAccepted(consentContent.version));
  };

  const handleRejectConsent = () => {
    setConsentState(consentStorageFacade.persistRejected(consentContent.version));
  };

  const handleLocaleChange = (nextLocaleCode: LocaleCode) => {
    if (nextLocaleCode === localeCode) {
      return;
    }

    analyticsService.trackActionClick(activeRoute.routeKey, "topbar", "switch_locale", localeCode);
    setLocaleCode(nextLocaleCode);
  };

  const handleThemeChange = (nextThemeId: string) => {
    if (nextThemeId === themeId) {
      return;
    }

    analyticsService.trackActionClick(activeRoute.routeKey, "topbar", "switch_theme", localeCode);
    setThemeId(nextThemeId);
  };

  const handleExploreProjects = () => {
    analyticsService.trackActionClick(activeRoute.routeKey, "hero", "open_projects", localeCode);
    navigate("/projects");
  };

  const speakSummary = () => {
    analyticsService.trackActionClick(activeRoute.routeKey, "hero", "read_intro", localeCode);

    if (
      !portfolioContent.accessibility.speechSynthesisEnabled ||
      !("speechSynthesis" in window)
    ) {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(heroViewModel.summary);
    utterance.lang = localeCode === "ru" ? "ru-RU" : "en-US";
    window.speechSynthesis.speak(utterance);
  };

  if (isConsentRejected) {
    return (
      <div className="site-blocked">
        <div className="site-blocked__card">
          <p className="site-blocked__eyebrow">
            {localeCode === "ru" ? "Доступ остановлен" : "Access stopped"}
          </p>
          <h1 className="site-blocked__title">
            {localeCode === "ru"
              ? "Сайт закрыт, потому что согласие на обезличенную аналитику не было принято."
              : "The site is closed because consent for anonymous analytics was not accepted."}
          </h1>
          <p className="site-blocked__description">
            {localeCode === "ru"
              ? "Если браузер не закрыл страницу автоматически, можно просто закрыть вкладку."
              : "If the browser did not close the page automatically, you can close the tab manually."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="app-background" aria-hidden="true" />
      <PageShell>
        <header className="topbar">
          <Link
            className="brandmark"
            to="/"
            onClick={() =>
              analyticsService.trackActionClick(activeRoute.routeKey, "topbar", "open_home_brand", localeCode)
            }
          >
            {portfolioContent.seo.siteName[localeCode]}
          </Link>
          <nav className="topbar__nav" aria-label="Main navigation">
            <NavLink
              className="topbar__link"
              to="/"
              onClick={() =>
                analyticsService.trackActionClick(activeRoute.routeKey, "topbar", "open_profile", localeCode)
              }
            >
              {localeCode === "ru" ? "Профиль" : "Profile"}
            </NavLink>
            <NavLink
              className="topbar__link"
              to="/projects"
              onClick={() =>
                analyticsService.trackActionClick(activeRoute.routeKey, "topbar", "open_projects_nav", localeCode)
              }
            >
              {localeCode === "ru" ? "Проекты" : "Projects"}
            </NavLink>
          </nav>
          <div className="topbar__controls">
            <LocaleSwitcher
              currentLocale={localeCode}
              availableLocales={localeService.getLocaleOptions()}
              onLocaleChange={handleLocaleChange}
            />
            <ThemeSwitcher
              currentThemeId={themeId}
              themes={themeService.getThemeOptions(localeCode)}
              onThemeChange={handleThemeChange}
            />
          </div>
        </header>

        <div className="runtime-note">
          <span className={`runtime-note__badge runtime-note__badge--${contentSource}`}>
            {contentSource === "live_api" ? "Live API" : "Preview fallback"}
          </span>
          <span className="runtime-note__text">
            {contentSource === "live_api"
              ? "Публичная витрина читает единый snapshot из backend API."
              : "Публичная витрина временно использует встроенный preview snapshot."}
          </span>
        </div>

        {portfolioLoadError ? (
          <div className="runtime-alert">
            <strong>Portfolio API fallback:</strong> {portfolioLoadError}
          </div>
        ) : null}

        <main className="main-content">
          <AppRouter
            localeCode={localeCode}
            heroViewModel={heroViewModel}
            projectCards={projectCards}
            onSpeakSummary={speakSummary}
            onExploreProjects={handleExploreProjects}
          />
        </main>
      </PageShell>
      {shouldPromptConsent ? (
        <ConsentModal
          localeCode={localeCode}
          content={consentContent}
          onAccept={handleAcceptConsent}
          onReject={handleRejectConsent}
        />
      ) : null}
    </>
  );
}
