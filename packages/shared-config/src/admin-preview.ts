import type {
  AnalyticsDashboardSnapshot,
  AdminAuditLogEntry,
  AdminContentStateSnapshot,
  BackupArtifactSummary,
  ImportCandidateSummary,
  RuntimeHealthSnapshot,
} from "@portfolio/shared-types";

/**
 * Preview-данные для административной панели.
 *
 * Они позволяют собрать UI до подключения настоящих backend-репозиториев,
 * аналитических агрегатов и backup-реестра.
 */
export const analyticsDashboardPreview: AnalyticsDashboardSnapshot = {
  sourceKind: "preview_fallback",
  sessionsLast7Days: [
    { label: "D-6", value: 0, blockedValue: 0 },
    { label: "D-5", value: 0, blockedValue: 0 },
    { label: "D-4", value: 0, blockedValue: 0 },
    { label: "D-3", value: 0, blockedValue: 0 },
    { label: "D-2", value: 0, blockedValue: 0 },
    { label: "D-1", value: 0, blockedValue: 0 },
    { label: "D", value: 0, blockedValue: 0 },
  ],
  viewsLast7Days: [
    { label: "D-6", value: 0, blockedValue: 0 },
    { label: "D-5", value: 0, blockedValue: 0 },
    { label: "D-4", value: 0, blockedValue: 0 },
    { label: "D-3", value: 0, blockedValue: 0 },
    { label: "D-2", value: 0, blockedValue: 0 },
    { label: "D-1", value: 0, blockedValue: 0 },
    { label: "D", value: 0, blockedValue: 0 },
  ],
  clicksLast7Days: [
    { label: "D-6", value: 0, blockedValue: 0 },
    { label: "D-5", value: 0, blockedValue: 0 },
    { label: "D-4", value: 0, blockedValue: 0 },
    { label: "D-3", value: 0, blockedValue: 0 },
    { label: "D-2", value: 0, blockedValue: 0 },
    { label: "D-1", value: 0, blockedValue: 0 },
    { label: "D", value: 0, blockedValue: 0 },
  ],
  topSections: [],
  topActions: [],
  allTimeTotals: {
    sessions: 0,
    sectionViews: 0,
    sectionClicks: 0,
  },
};

export const backupArtifactsPreview: BackupArtifactSummary[] = [
  {
    backupId: "backup-2026-08-03-published",
    backupKind: "export_bundle",
    snapshotKind: "published",
    fileName: "portfolio-published-2026-08-03.bundle.json",
    checksumSha256: "9cbf9d5d0c5f7f3566d69d6f4bc1acfe8f2ef8c710d10e6380ad8f14b9d94f0f",
    contentSchemaVersion: "portfolio.v1",
    fileSizeBytes: 82432,
    createdAt: "2026-08-03T14:15:00Z",
    createdByActor: "admin@example.com",
  },
  {
    backupId: "backup-2026-08-02-before-replace",
    backupKind: "pre_replace_backup",
    snapshotKind: "before_replace",
    fileName: "portfolio-before-replace-2026-08-02.bundle.json",
    checksumSha256: "a4f5c8d6b6b19f66795f6ecae8cf80d6264ed7df51ea0bcd4787fa3f04ea2088",
    contentSchemaVersion: "portfolio.v1",
    fileSizeBytes: 80111,
    createdAt: "2026-08-02T09:40:00Z",
    createdByActor: "admin@example.com",
  },
];

export const importCandidatesPreview: ImportCandidateSummary[] = [
  {
    importCandidateId: "candidate-2026-08-03-resume",
    parseStatus: "warning",
    contentSchemaVersion: "portfolio.v1",
    createdAt: "2026-08-03T15:00:00Z",
    createdByActor: "admin@example.com",
    reviewSummary: {
      replaceableSections: ["profile", "projects", "experience"],
      warningsCount: 1,
      canReplaceFully: true,
    },
  },
];

export const runtimeHealthPreview: RuntimeHealthSnapshot = {
  sourceKind: "internal-probe",
  updatedAt: "2026-08-03T15:40:00Z",
  services: {
    api: "ok",
    postgres: "ok",
    redis: "ok",
  },
  diskFreeMb: 6120,
  memoryPressure: "low",
  grafanaEnabled: false,
};

export const adminContentStatePreview: AdminContentStateSnapshot = {
  stateKey: "content_admin",
  sourceMetadata: {
    lastSourceType: "resume_pdf",
    lastSourceFilename: "resume-2026-07-22.pdf",
    warnings: ["Не удалось однозначно определить даты по одному месту работы."],
    manualOverrides: ["profile.summary.ru", "projects[0].summary.en"],
  },
  lastImportStatus: "warning",
  lastImportedAt: "2026-08-03T15:00:00Z",
  pendingImportCandidateId: "candidate-2026-08-03-resume",
  currentBackupArtifactId: "backup-2026-08-03-published",
  updatedAt: "2026-08-03T15:05:00Z",
};

export const adminAuditLogPreview: AdminAuditLogEntry[] = [
  {
    logId: "log-2026-08-03-publish",
    occurredAt: "2026-08-03T15:12:00Z",
    actorLogin: "admin@example.com",
    actionCode: "publish_snapshot",
    entityType: "portfolio_snapshot",
    entityKey: "published",
    resultCode: "success",
  },
  {
    logId: "log-2026-08-03-import-review",
    occurredAt: "2026-08-03T15:02:00Z",
    actorLogin: "admin@example.com",
    actionCode: "create_import_candidate",
    entityType: "import_candidate",
    entityKey: "candidate-2026-08-03-resume",
    resultCode: "warning",
  },
];
