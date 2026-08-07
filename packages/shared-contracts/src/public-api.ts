import type {
  AnalyticsDashboardSnapshot,
  AnalyticsEventIngestResult,
  AnalyticsSectionClickEventPayload,
  AnalyticsSectionViewEventPayload,
  AnalyticsSessionEventPayload,
  AdminAuditLogEntry,
  AdminContentStateSnapshot,
  BackupArtifactSummary,
  ContentDiffSnapshot,
  ContentAssetSummary,
  ImportApplyMode,
  ImportCandidateFieldReview,
  ImportCandidateSummary,
  PortfolioContent,
  RuntimeHealthSnapshot,
} from "@portfolio/shared-types";

/**
 * Контракты первого публичного API.
 *
 * Сейчас они используются как общая договорённость между frontend и backend-скелетом.
 */
export interface PublicPortfolioResponse {
  snapshotKind: "published" | "draft";
  contentSchemaVersion: PortfolioContent["version"];
  contentChecksumSha256: string;
  updatedAt: string;
  payload: PortfolioContent;
}

export interface ProjectListResponse {
  items: PortfolioContent["projects"];
  total: number;
}

export interface AdminExportResponse {
  version: PortfolioContent["version"];
  payload: PortfolioContent;
}

export interface DraftSnapshotUpsertRequest {
  payload: PortfolioContent;
}

export interface ContentAssetListResponse {
  items: ContentAssetSummary[];
}

export interface AdminLoginRequest {
  login: string;
  password: string;
}

export interface AdminSessionResponse {
  login: string;
  csrfToken: string;
  expiresAt: string;
}

export interface AdminPublishResponse {
  snapshot: PublicPortfolioResponse;
  backup: BackupArtifactSummary | null;
}

export interface AdminContentStateResponse {
  snapshot: AdminContentStateSnapshot;
}

export interface AnalyticsSummaryResponse {
  snapshot: AnalyticsDashboardSnapshot;
}

export interface AnalyticsEventIngestResponse {
  result: AnalyticsEventIngestResult;
}

export interface AnalyticsSessionIngestRequest {
  event: AnalyticsSessionEventPayload;
}

export interface AnalyticsSectionViewIngestRequest {
  event: AnalyticsSectionViewEventPayload;
}

export interface AnalyticsSectionClickIngestRequest {
  event: AnalyticsSectionClickEventPayload;
}

export interface BackupArtifactListResponse {
  items: BackupArtifactSummary[];
}

export interface CreateBackupArtifactRequest {
  snapshotKind: "draft" | "published";
  backupKind: "export_bundle" | "manual_backup";
}

export interface BackupArtifactMutationResponse {
  item: BackupArtifactSummary;
}

export interface ImportCandidateListResponse {
  items: ImportCandidateSummary[];
}

export interface ImportCandidateMutationResponse {
  item: ImportCandidateSummary;
}

export interface ImportCandidateFieldReviewResponse {
  item: ImportCandidateSummary;
  fields: ImportCandidateFieldReview[];
}

export interface ImportCandidateFieldPatch {
  path: string;
  operation: "set" | "remove";
  value?: unknown;
}

export interface ImportCandidateApplyRequest {
  replaceMode: ImportApplyMode;
  sections: string[];
  fields: ImportCandidateFieldPatch[];
}

export interface ImportCandidateApplyResponse {
  snapshot: PublicPortfolioResponse;
  backup: BackupArtifactSummary | null;
  item: ImportCandidateSummary;
  replaceMode: ImportApplyMode;
  appliedSections: string[];
  appliedFields: string[];
}

export interface ContentDiffResponse {
  diff: ContentDiffSnapshot;
}

export interface RuntimeHealthResponse {
  snapshot: RuntimeHealthSnapshot;
}

export interface AuditLogListResponse {
  items: AdminAuditLogEntry[];
}
