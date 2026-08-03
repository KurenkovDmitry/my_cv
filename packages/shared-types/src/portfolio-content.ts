export type LocaleCode = "ru" | "en";

/**
 * Локализуемая строка.
 *
 * Формат намеренно простой, чтобы его можно было хранить в YAML, JSON и БД
 * без отдельного движка переводов на первом этапе.
 */
export interface LocalizedText {
  ru: string;
  en: string;
}

export interface ProfileContent {
  slug: string;
  displayName: LocalizedText;
  headline: LocalizedText;
  summary: LocalizedText;
  location: LocalizedText;
  avatarAsset: string;
}

export interface EducationItem {
  id: string;
  title: LocalizedText;
  status: "draft" | "published" | "needs_review";
}

export interface ProjectLink {
  kind: "repository" | "case-study" | "demo";
  label: LocalizedText;
  href: string;
}

export interface ProjectContent {
  id: string;
  slug: string;
  featured: boolean;
  status: "active" | "archived" | "draft";
  title: LocalizedText;
  summary: LocalizedText;
  technologies: string[];
  links: ProjectLink[];
}

export interface ExperienceItem {
  id: string;
  company: LocalizedText;
  role: LocalizedText;
  status: "published" | "needs_review";
}

export interface ThemeDefinition {
  id: string;
  label: LocalizedText;
}

export interface ThemeCollection {
  active: string;
  available: ThemeDefinition[];
}

export interface LocalizationConfig {
  defaultLocale: LocaleCode;
  supportedLocales: LocaleCode[];
  autoDetectByRegion: Record<string, LocaleCode>;
}

export interface AccessibilityConfig {
  speechSynthesisEnabled: boolean;
  highContrastModeEnabled: boolean;
  reducedMotionPresetEnabled: boolean;
}

export interface SeoConfig {
  siteName: LocalizedText;
  openGraphImage: string;
}

export interface AnalyticsConsentContent {
  version: string;
  modalTitle: LocalizedText;
  modalBodyMarkdown: LocalizedText;
  acceptButtonLabel: LocalizedText;
  rejectButtonLabel: LocalizedText;
}

export interface LegalContent {
  analyticsConsent: AnalyticsConsentContent;
}

export type ConsentDecision = "accepted" | "rejected" | "unknown";

export type AnalyticsStorageMode =
  | "local_storage"
  | "indexed_db"
  | "session_storage"
  | "http_only_cookie"
  | "memory_only";

export interface ConsentStateSnapshot {
  version: string;
  state: ConsentDecision;
  storageMode: AnalyticsStorageMode;
  updatedAt: string;
}

export interface BackupArtifactSummary {
  backupId: string;
  backupKind: "export_bundle" | "pre_replace_backup" | "manual_backup";
  snapshotKind: "draft" | "published" | "before_replace";
  fileName: string;
  checksumSha256: string;
  contentSchemaVersion: string;
  fileSizeBytes: number;
  createdAt: string;
  createdByActor: string;
}

export interface ImportCandidateSummary {
  importCandidateId: string;
  parseStatus: "parsed" | "warning" | "failed";
  contentSchemaVersion: string;
  createdAt: string;
  createdByActor: string;
  reviewSummary: {
    replaceableSections: string[];
    warningsCount: number;
    canReplaceFully: boolean;
  };
}

export type ImportApplyMode = "full_replace" | "partial_replace";

export interface ContentDiffSummary {
  changedPathsCount: number;
  sectionsChangedCount: number;
}

export interface ContentDiffSnapshot {
  leftLabel: string;
  rightLabel: string;
  changedPaths: string[];
  sections: string[];
  summary: ContentDiffSummary;
}

export interface AnalyticsSeriesPoint {
  label: string;
  value: number;
  blockedValue?: number;
}

export interface AnalyticsSectionTotal {
  key: string;
  label: LocalizedText;
  total: number;
}

export interface AnalyticsActionTotal {
  key: string;
  label: LocalizedText;
  total: number;
}

export interface AnalyticsDashboardSnapshot {
  sessionsLast7Days: AnalyticsSeriesPoint[];
  viewsLast7Days: AnalyticsSeriesPoint[];
  clicksLast7Days: AnalyticsSeriesPoint[];
  topSections: AnalyticsSectionTotal[];
  topActions: AnalyticsActionTotal[];
  allTimeTotals: {
    sessions: number;
    sectionViews: number;
    sectionClicks: number;
  };
}

export interface RuntimeHealthSnapshot {
  sourceKind: string;
  updatedAt: string;
  services: {
    api: "ok" | "degraded" | "failed";
    postgres: "ok" | "degraded" | "failed";
    redis: "ok" | "degraded" | "failed";
  };
  diskFreeMb: number;
  memoryPressure: "low" | "medium" | "high";
  grafanaEnabled: boolean;
}

export interface AdminContentStateSnapshot {
  stateKey: string;
  sourceMetadata: Record<string, unknown>;
  lastImportStatus: string;
  lastImportedAt: string | null;
  pendingImportCandidateId: string | null;
  currentBackupArtifactId: string | null;
  updatedAt: string;
}

export interface AdminAuditLogEntry {
  logId: string;
  occurredAt: string;
  actorLogin: string | null;
  actionCode: string;
  entityType: string;
  entityKey: string | null;
  resultCode: string;
}

export interface AnalyticsSessionEventPayload {
  entryRouteKey: string;
  localeCode: LocaleCode;
  consentState: "accepted";
  storageMode: AnalyticsStorageMode;
  sessionNonce: string;
  occurredAt: string;
}

export interface AnalyticsSectionViewEventPayload {
  routeKey: string;
  sectionKey: string;
  localeCode: LocaleCode;
  viewSource: "ssr_render" | "viewport_visible" | "rehydrated_visible";
  sessionNonce: string;
  occurredAt: string;
}

export interface AnalyticsSectionClickEventPayload {
  routeKey: string;
  sectionKey: string;
  actionKey: string;
  localeCode: LocaleCode;
  sessionNonce: string;
  occurredAt: string;
}

export interface AnalyticsEventIngestResult {
  status: "accepted" | "blocked" | "deduplicated";
  blockedReason?: string;
}

/**
 * Переносимый формат контента сайта.
 */
export interface PortfolioContent {
  version: "portfolio.v1";
  draft: boolean;
  needsManualReview: boolean;
  profile: ProfileContent;
  education: EducationItem[];
  projects: ProjectContent[];
  experience: ExperienceItem[];
  skills: {
    focusAreas: string[];
  };
  themes: ThemeCollection;
  localization: LocalizationConfig;
  accessibility: AccessibilityConfig;
  legal: LegalContent;
  seo: SeoConfig;
}
