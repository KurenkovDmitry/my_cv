import { frontendEnvConfig } from "@portfolio/shared-config";
import type {
  AdminContentStateResponse,
  AdminPublishResponse,
  AnalyticsSummaryResponse,
  AuditLogListResponse,
  BackupArtifactListResponse,
  BackupArtifactMutationResponse,
  ContentDiffResponse,
  CreateBackupArtifactRequest,
  DraftSnapshotUpsertRequest,
  ImportCandidateApplyRequest,
  ImportCandidateApplyResponse,
  ImportCandidateListResponse,
  ImportCandidateMutationResponse,
  PublicPortfolioResponse,
  RuntimeHealthResponse,
} from "@portfolio/shared-contracts";
import { requestAdminJson } from "./admin-auth-http-client";

/**
 * Собирает все admin dashboard payload в одном месте.
 */
export async function fetchAdminDashboardData(signal?: AbortSignal) {
  const [
    portfolioResponse,
    analyticsResponse,
    contentStateResponse,
    backupResponse,
    importCandidateResponse,
    runtimeHealthResponse,
    auditLogResponse,
  ] = await Promise.all([
    requestAdminJson<PublicPortfolioResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/content/snapshot?kind=draft`,
      { method: "GET" },
      signal,
    ),
    requestAdminJson<AnalyticsSummaryResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/analytics/summary`,
      { method: "GET" },
      signal,
    ),
    requestAdminJson<AdminContentStateResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/system/content-state`,
      { method: "GET" },
      signal,
    ),
    requestAdminJson<BackupArtifactListResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/system/backups`,
      { method: "GET" },
      signal,
    ),
    requestAdminJson<ImportCandidateListResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/system/import-candidates`,
      { method: "GET" },
      signal,
    ),
    requestAdminJson<RuntimeHealthResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/system/runtime-health`,
      { method: "GET" },
      signal,
    ),
    requestAdminJson<AuditLogListResponse>(
      `${frontendEnvConfig.adminApiBaseUrl}/system/audit-log`,
      { method: "GET" },
      signal,
    ),
  ]);

  return {
    portfolioResponse,
    analyticsResponse,
    contentStateResponse,
    backupResponse,
    importCandidateResponse,
    runtimeHealthResponse,
    auditLogResponse,
  };
}

export async function saveDraftSnapshot(requestPayload: DraftSnapshotUpsertRequest) {
  return requestAdminJson<PublicPortfolioResponse>(`${frontendEnvConfig.adminApiBaseUrl}/content/draft`, {
    method: "PUT",
    body: JSON.stringify(requestPayload),
  });
}

export async function publishDraftSnapshot() {
  return requestAdminJson<AdminPublishResponse>(`${frontendEnvConfig.adminApiBaseUrl}/content/publish`, {
    method: "POST",
  });
}

export async function createBackupArtifact(requestPayload: CreateBackupArtifactRequest) {
  return requestAdminJson<BackupArtifactMutationResponse>(`${frontendEnvConfig.adminApiBaseUrl}/system/backups`, {
    method: "POST",
    body: JSON.stringify(requestPayload),
  });
}

export async function deleteBackupArtifact(backupId: string) {
  return requestAdminJson<BackupArtifactMutationResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/backups/${backupId}`,
    {
      method: "DELETE",
    },
  );
}

export function getBackupDownloadUrl(backupId: string): string {
  return `${frontendEnvConfig.adminApiBaseUrl}/system/backups/${backupId}/download`;
}

export async function compareBackupToSnapshot(
  backupId: string,
  snapshotKind: "draft" | "published" = "draft",
) {
  return requestAdminJson<ContentDiffResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/backups/${backupId}/compare/snapshot?snapshotKind=${snapshotKind}`,
    { method: "GET" },
  );
}

export async function compareBackupToBackup(leftBackupId: string, rightBackupId: string) {
  return requestAdminJson<ContentDiffResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/backups/${leftBackupId}/compare/backup/${rightBackupId}`,
    { method: "GET" },
  );
}

export async function uploadImportCandidate(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return requestAdminJson<ImportCandidateMutationResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/import-candidates`,
    {
      method: "POST",
      body: formData,
    },
  );
}

export async function compareImportCandidateToSnapshot(
  importCandidateId: string,
  snapshotKind: "draft" | "published" = "draft",
) {
  return requestAdminJson<ContentDiffResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/import-candidates/${importCandidateId}/compare/snapshot?snapshotKind=${snapshotKind}`,
    { method: "GET" },
  );
}

export async function compareImportCandidateToBackup(importCandidateId: string, backupId: string) {
  return requestAdminJson<ContentDiffResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/import-candidates/${importCandidateId}/compare/backup/${backupId}`,
    { method: "GET" },
  );
}

export async function applyImportCandidateToDraft(
  importCandidateId: string,
  requestPayload: ImportCandidateApplyRequest,
) {
  return requestAdminJson<ImportCandidateApplyResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/system/import-candidates/${importCandidateId}/apply-to-draft`,
    {
      method: "POST",
      body: JSON.stringify(requestPayload),
    },
  );
}
