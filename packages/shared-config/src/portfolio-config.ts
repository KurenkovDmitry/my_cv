import type { PortfolioContent } from "@portfolio/shared-types";

/**
 * Временный preview-контент.
 *
 * До подключения backend и импорта YAML этот объект позволяет
 * собрать и проверить frontend-контур без моков в каждом модуле.
 */
export const portfolioPreviewContent: PortfolioContent = {
  version: "portfolio.v1",
  draft: true,
  needsManualReview: true,
  profile: {
    slug: "primary",
    displayName: {
      ru: "Д. А. Куренков",
      en: "D. A. Kurenkov"
    },
    headline: {
      ru: "Инженер, который соединяет highload-мышление, инфраструктуру и аккуратный интерфейс.",
      en: "An engineer connecting highload thinking, infrastructure, and refined interface design."
    },
    summary: {
      ru: "Этот стартовый профиль собран как демонстрационная база для будущего импорта данных из резюме и административного редактирования.",
      en: "This starter profile acts as a demonstration baseline for upcoming CV import and admin editing."
    },
    location: {
      ru: "Россия",
      en: "Russia"
    },
    avatarAsset: "/rules/photo_2025-04-09_22-18-09.jpg"
  },
  education: [
    {
      id: "school-204",
      title: {
        ru: "Школа №204",
        en: "School No. 204"
      },
      status: "needs_review"
    },
    {
      id: "bmstu",
      title: {
        ru: "МГТУ имени Н. Э. Баумана",
        en: "Bauman Moscow State Technical University"
      },
      status: "needs_review"
    }
  ],
  projects: [
    {
      id: "portfolio-platform",
      slug: "portfolio-platform",
      featured: true,
      status: "active",
      title: {
        ru: "Платформа персонального портфолио",
        en: "Personal portfolio platform"
      },
      summary: {
        ru: "Многомодульный SPA-каркас с публичной витриной, административной панелью и безопасным backend-контуром.",
        en: "A multi-module SPA foundation with a public showcase, admin panel, and secure backend layer."
      },
      technologies: ["TypeScript", "React", "SCSS", "FastAPI", "PostgreSQL", "Redis"],
      links: [
        {
          kind: "repository",
          label: {
            ru: "Исходный код",
            en: "Source code"
          },
          href: "#"
        }
      ]
    }
  ],
  experience: [
    {
      id: "cv-import-pending",
      company: {
        ru: "Импорт из резюме в процессе",
        en: "CV import pending"
      },
      role: {
        ru: "После подключения парсера данные опыта будут перенесены в модульный формат.",
        en: "Experience details will be moved into the modular format after the parser is connected."
      },
      status: "needs_review"
    }
  ],
  skills: {
    focusAreas: ["Highload architecture", "Routing", "Nginx", "Infrastructure", "Frontend architecture"]
  },
  themes: {
    active: "paper-sand",
    available: [
      {
        id: "paper-sand",
        label: {
          ru: "Тёплый песок",
          en: "Paper sand"
        }
      },
      {
        id: "contrast-carbon",
        label: {
          ru: "Контрастный графит",
          en: "Contrast carbon"
        }
      }
    ]
  },
  localization: {
    defaultLocale: "en",
    supportedLocales: ["en", "ru"],
    autoDetectByRegion: {
      RU: "ru"
    }
  },
  accessibility: {
    speechSynthesisEnabled: true,
    highContrastModeEnabled: true,
    reducedMotionPresetEnabled: true
  },
  legal: {
    analyticsConsent: {
      version: "2026-08-03",
      modalTitle: {
        ru: "Согласие на обезличенную аналитику",
        en: "Consent for anonymous analytics",
      },
      modalBodyMarkdown: {
        ru: "Сайт собирает только обезличенную агрегированную статистику просмотров, кликов и числа сессий. Данные не привязываются к IP, личности или постоянному идентификатору устройства.",
        en: "The site collects only anonymous aggregated statistics about views, clicks, and session counts. The data is not tied to IP, identity, or a permanent device identifier.",
      },
      acceptButtonLabel: {
        ru: "Продолжить и согласиться",
        en: "Continue and agree",
      },
      rejectButtonLabel: {
        ru: "Отказаться и закрыть сайт",
        en: "Decline and close site",
      },
    },
  },
  seo: {
    siteName: {
      ru: "Портфолио Д. А. Куренкова",
      en: "D. A. Kurenkov Portfolio"
    },
    openGraphImage: "/rules/photo_2025-04-09_22-18-09.jpg"
  }
};
