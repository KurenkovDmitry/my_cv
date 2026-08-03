import { ChangeEvent, startTransition, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import {
  adminAuditLogPreview,
  adminContentStatePreview,
  analyticsDashboardPreview,
  backupArtifactsPreview,
  importCandidatesPreview,
  portfolioPreviewContent,
  runtimeHealthPreview,
} from "@portfolio/shared-config";
import type {
  AdminAuditLogEntry,
  AdminContentStateSnapshot,
  AnalyticsDashboardSnapshot,
  AnalyticsSeriesPoint,
  BackupArtifactSummary,
  ContentDiffSnapshot,
  ImportApplyMode,
  ImportCandidateSummary,
  PortfolioContent,
  RuntimeHealthSnapshot,
} from "@portfolio/shared-types";
import {
  applyImportCandidateToDraft,
  compareBackupToBackup,
  compareBackupToSnapshot,
  compareImportCandidateToBackup,
  compareImportCandidateToSnapshot,
  createBackupArtifact,
  deleteBackupArtifact,
  fetchAdminDashboardData,
  getBackupDownloadUrl,
  publishDraftSnapshot,
  saveDraftSnapshot,
  uploadImportCandidate,
} from "./admin-dashboard-http-client";

type DashboardSourceKind = "live_api" | "preview_fallback";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 ** 2) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

function getSeriesMaxValue(series: AnalyticsSeriesPoint[]): number {
  return Math.max(
    1,
    ...series.map((point) => Math.max(point.value, point.blockedValue ?? 0)),
  );
}

function pickStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
}

function mergeCandidateSelections(
  currentSelections: Record<string, string[]>,
  candidateItems: ImportCandidateSummary[],
): Record<string, string[]> {
  const nextSelections: Record<string, string[]> = {};

  for (const candidateItem of candidateItems) {
    const availableSections = candidateItem.reviewSummary.replaceableSections;
    const currentCandidateSelection = currentSelections[candidateItem.importCandidateId] ?? [];
    const filteredSelection = currentCandidateSelection.filter((sectionName) =>
      availableSections.includes(sectionName),
    );

    nextSelections[candidateItem.importCandidateId] =
      filteredSelection.length > 0 ? filteredSelection : availableSections;
  }

  return nextSelections;
}

/**
 * Первая административная витрина.
 *
 * Сейчас она уже показывает ключевые контуры будущей панели:
 * draft-редактирование, preview, аналитику, import control version,
 * backup registry, service-state, health и audit log.
 */
export function App() {
  const [draftContent, setDraftContent] = useState<PortfolioContent>(() =>
    structuredClone(portfolioPreviewContent),
  );
  const [previewLocale, setPreviewLocale] = useState<"ru" | "en">("ru");
  const [dashboardSource, setDashboardSource] = useState<DashboardSourceKind>("preview_fallback");
  const [dashboardLoadError, setDashboardLoadError] = useState<string | null>(null);
  const [analyticsSnapshot, setAnalyticsSnapshot] = useState<AnalyticsDashboardSnapshot>(analyticsDashboardPreview);
  const [contentState, setContentState] = useState<AdminContentStateSnapshot>(adminContentStatePreview);
  const [backupArtifacts, setBackupArtifacts] = useState<BackupArtifactSummary[]>(backupArtifactsPreview);
  const [importCandidates, setImportCandidates] = useState<ImportCandidateSummary[]>(importCandidatesPreview);
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealthSnapshot>(runtimeHealthPreview);
  const [auditLogs, setAuditLogs] = useState<AdminAuditLogEntry[]>(adminAuditLogPreview);
  const [candidateSelections, setCandidateSelections] = useState<Record<string, string[]>>({});
  const [currentDiff, setCurrentDiff] = useState<ContentDiffSnapshot | null>(null);
  const [mutationFeedback, setMutationFeedback] = useState<string | null>(null);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isPublishingDraft, setIsPublishingDraft] = useState(false);
  const [isCreatingDraftBackup, setIsCreatingDraftBackup] = useState(false);
  const [isUploadingImportCandidate, setIsUploadingImportCandidate] = useState(false);
  const [busyBackupId, setBusyBackupId] = useState<string | null>(null);
  const [busyDiffKey, setBusyDiffKey] = useState<string | null>(null);
  const [busyImportActionKey, setBusyImportActionKey] = useState<string | null>(null);
  const hasLocalDraftChangesRef = useRef(false);

  const deferredDraftContent = useDeferredValue(draftContent);
  const firstProject = draftContent.projects[0];
  const canRenderProjectEditor = Boolean(firstProject);
  const consentContent = deferredDraftContent.legal.analyticsConsent;

  const exportFileName = useMemo(() => {
    const dateStamp = new Date().toISOString().slice(0, 10);
    return `portfolio-draft-${dateStamp}.json`;
  }, []);

  const sessionSeriesMax = useMemo(
    () => getSeriesMaxValue(analyticsSnapshot.sessionsLast7Days),
    [analyticsSnapshot.sessionsLast7Days],
  );
  const viewSeriesMax = useMemo(
    () => getSeriesMaxValue(analyticsSnapshot.viewsLast7Days),
    [analyticsSnapshot.viewsLast7Days],
  );
  const clickSeriesMax = useMemo(
    () => getSeriesMaxValue(analyticsSnapshot.clicksLast7Days),
    [analyticsSnapshot.clicksLast7Days],
  );

  const applyDashboardData = ({
    portfolioResponse,
    analyticsResponse,
    contentStateResponse,
    backupResponse,
    importCandidateResponse,
    runtimeHealthResponse,
    auditLogResponse,
  }: Awaited<ReturnType<typeof fetchAdminDashboardData>>) => {
    if (!hasLocalDraftChangesRef.current) {
      setDraftContent(portfolioResponse.payload);
    }

    setAnalyticsSnapshot(analyticsResponse.snapshot);
    setContentState(contentStateResponse.snapshot);
    setBackupArtifacts(backupResponse.items);
    setImportCandidates(importCandidateResponse.items);
    setCandidateSelections((currentSelections) =>
      mergeCandidateSelections(currentSelections, importCandidateResponse.items),
    );
    setRuntimeHealth(runtimeHealthResponse.snapshot);
    setAuditLogs(auditLogResponse.items);
    setDashboardSource("live_api");
    setDashboardLoadError(null);
  };

  const loadDashboardData = async (signal?: AbortSignal) => {
    const dashboardData = await fetchAdminDashboardData(signal);
    applyDashboardData(dashboardData);
  };

  useEffect(() => {
    const abortController = new AbortController();

    void (async () => {
      try {
        await loadDashboardData(abortController.signal);
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }

        setDashboardSource("preview_fallback");
        setDashboardLoadError(error instanceof Error ? error.message : "Unknown admin dashboard loading error.");
      }
    })();

    return () => abortController.abort();
  }, []);

  const updateProfileField = (
    fieldName: "displayName" | "headline" | "summary",
    localeCode: "ru" | "en",
    value: string,
  ) => {
    hasLocalDraftChangesRef.current = true;

    startTransition(() => {
      setDraftContent((currentContent) => ({
        ...currentContent,
        profile: {
          ...currentContent.profile,
          [fieldName]: {
            ...currentContent.profile[fieldName],
            [localeCode]: value,
          },
        },
      }));
    });
  };

  const updateFirstProjectField = (
    fieldName: "title" | "summary",
    localeCode: "ru" | "en",
    value: string,
  ) => {
    hasLocalDraftChangesRef.current = true;

    startTransition(() => {
      setDraftContent((currentContent) => ({
        ...currentContent,
        projects: currentContent.projects.map((projectItem, projectIndex) =>
          projectIndex !== 0
            ? projectItem
            : {
                ...projectItem,
                [fieldName]: {
                  ...projectItem[fieldName],
                  [localeCode]: value,
                },
              },
        ),
      }));
    });
  };

  const handleDraftImport = async (event: ChangeEvent<HTMLInputElement>) => {
    const importFile = event.target.files?.[0];

    if (!importFile) {
      return;
    }

    const fileText = await importFile.text();
    const importedDraft = JSON.parse(fileText) as PortfolioContent;
    hasLocalDraftChangesRef.current = true;

    startTransition(() => {
      setDraftContent(importedDraft);
    });
    setMutationFeedback("Локальный draft загружен в форму. Чтобы он попал в backend snapshot, сохраните его.");

    event.target.value = "";
  };

  const handleImportCandidateUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const importFile = event.target.files?.[0];

    if (!importFile) {
      return;
    }

    try {
      setIsUploadingImportCandidate(true);
      setMutationFeedback(null);
      const uploadResponse = await uploadImportCandidate(importFile);
      await loadDashboardData();
      setMutationFeedback(`Импорт-кандидат ${uploadResponse.item.importCandidateId} загружен на review.`);
    } catch (error) {
      setMutationFeedback(
        error instanceof Error ? error.message : "Не удалось загрузить import candidate.",
      );
    } finally {
      setIsUploadingImportCandidate(false);
      event.target.value = "";
    }
  };

  const handleDraftExport = () => {
    const fileBlob = new Blob([JSON.stringify(draftContent, null, 2)], {
      type: "application/json",
    });
    const objectUrl = URL.createObjectURL(fileBlob);
    const downloadLink = document.createElement("a");
    downloadLink.href = objectUrl;
    downloadLink.download = exportFileName;
    downloadLink.click();
    URL.revokeObjectURL(objectUrl);
  };

  const persistCurrentDraft = async () => {
    const savedDraftResponse = await saveDraftSnapshot({
      payload: draftContent,
    });
    hasLocalDraftChangesRef.current = false;
    setDraftContent(savedDraftResponse.payload);
    return savedDraftResponse;
  };

  const handleDraftSave = async () => {
    try {
      setIsSavingDraft(true);
      setMutationFeedback(null);
      await persistCurrentDraft();
      await loadDashboardData();
      setMutationFeedback("Draft snapshot сохранен в backend.");
    } catch (error) {
      setMutationFeedback(error instanceof Error ? error.message : "Не удалось сохранить draft snapshot.");
    } finally {
      setIsSavingDraft(false);
    }
  };

  const handleDraftPublish = async () => {
    try {
      setIsPublishingDraft(true);
      setMutationFeedback(null);

      if (hasLocalDraftChangesRef.current) {
        await persistCurrentDraft();
      }

      const publishResponse = await publishDraftSnapshot();
      hasLocalDraftChangesRef.current = false;
      await loadDashboardData();
      setMutationFeedback(
        publishResponse.backup
          ? `Published snapshot обновлен, а предыдущая версия сохранена в backup ${publishResponse.backup.fileName}.`
          : "Published snapshot обновлен.",
      );
    } catch (error) {
      setMutationFeedback(error instanceof Error ? error.message : "Не удалось опубликовать draft snapshot.");
    } finally {
      setIsPublishingDraft(false);
    }
  };

  const handleDraftBackupCreate = async () => {
    try {
      setIsCreatingDraftBackup(true);
      setMutationFeedback(null);

      if (hasLocalDraftChangesRef.current) {
        await persistCurrentDraft();
      }

      const backupResponse = await createBackupArtifact({
        snapshotKind: "draft",
        backupKind: "manual_backup",
      });
      await loadDashboardData();
      setMutationFeedback(`Создан backup ${backupResponse.item.fileName}.`);
    } catch (error) {
      setMutationFeedback(error instanceof Error ? error.message : "Не удалось создать backup draft.");
    } finally {
      setIsCreatingDraftBackup(false);
    }
  };

  const handleBackupDelete = async (backupId: string) => {
    const isConfirmed = window.confirm("Удалить backup из registry и физически удалить его файл?");
    if (!isConfirmed) {
      return;
    }

    try {
      setBusyBackupId(backupId);
      setMutationFeedback(null);
      const deleteResponse = await deleteBackupArtifact(backupId);
      await loadDashboardData();
      setMutationFeedback(`Backup ${deleteResponse.item.fileName} удален.`);
    } catch (error) {
      setMutationFeedback(error instanceof Error ? error.message : "Не удалось удалить backup.");
    } finally {
      setBusyBackupId(null);
    }
  };

  const handleBackupDownload = (backupId: string) => {
    window.open(getBackupDownloadUrl(backupId), "_blank", "noopener,noreferrer");
  };

  const resolvePreferredBackupId = (excludedBackupId?: string): string | null => {
    const preferredBackupIds = [
      contentState.currentBackupArtifactId,
      ...backupArtifacts.map((backupItem) => backupItem.backupId),
    ].filter((backupId): backupId is string => Boolean(backupId));

    return preferredBackupIds.find((backupId) => backupId !== excludedBackupId) ?? null;
  };

  const toggleCandidateSection = (importCandidateId: string, sectionName: string) => {
    setCandidateSelections((currentSelections) => {
      const currentCandidateSelection = currentSelections[importCandidateId] ?? [];
      const nextCandidateSelection = currentCandidateSelection.includes(sectionName)
        ? currentCandidateSelection.filter((entry) => entry !== sectionName)
        : [...currentCandidateSelection, sectionName].sort();

      return {
        ...currentSelections,
        [importCandidateId]: nextCandidateSelection,
      };
    });
  };

  const handleBackupCompare = async (backupId: string) => {
    const comparisonBackupId = resolvePreferredBackupId(backupId);
    const diffKey = `backup:${backupId}`;

    try {
      setBusyDiffKey(diffKey);
      setMutationFeedback(null);

      const diffResponse = comparisonBackupId
        ? await compareBackupToBackup(backupId, comparisonBackupId)
        : await compareBackupToSnapshot(backupId, "draft");

      setCurrentDiff(diffResponse.diff);
      setMutationFeedback(
        comparisonBackupId
          ? "Показан diff между выбранным backup и текущим опорным backup."
          : "Показан diff между выбранным backup и текущим draft snapshot.",
      );
    } catch (error) {
      setMutationFeedback(error instanceof Error ? error.message : "Не удалось построить diff для backup.");
    } finally {
      setBusyDiffKey(null);
    }
  };

  const handleImportCandidateCompareToDraft = async (importCandidateId: string) => {
    const diffKey = `candidate-draft:${importCandidateId}`;

    try {
      setBusyDiffKey(diffKey);
      setMutationFeedback(null);
      const diffResponse = await compareImportCandidateToSnapshot(importCandidateId, "draft");
      setCurrentDiff(diffResponse.diff);
      setMutationFeedback("Показан diff между import candidate и текущим draft snapshot.");
    } catch (error) {
      setMutationFeedback(
        error instanceof Error ? error.message : "Не удалось построить diff между кандидатом и draft.",
      );
    } finally {
      setBusyDiffKey(null);
    }
  };

  const handleImportCandidateCompareToBackup = async (importCandidateId: string) => {
    const comparisonBackupId = resolvePreferredBackupId();
    const diffKey = `candidate-backup:${importCandidateId}`;

    if (!comparisonBackupId) {
      setMutationFeedback("Сначала создайте хотя бы один backup, чтобы сравнить import candidate.");
      return;
    }

    try {
      setBusyDiffKey(diffKey);
      setMutationFeedback(null);
      const diffResponse = await compareImportCandidateToBackup(importCandidateId, comparisonBackupId);
      setCurrentDiff(diffResponse.diff);
      setMutationFeedback("Показан diff между import candidate и опорным backup.");
    } catch (error) {
      setMutationFeedback(
        error instanceof Error ? error.message : "Не удалось построить diff между кандидатом и backup.",
      );
    } finally {
      setBusyDiffKey(null);
    }
  };

  const handleImportCandidateApply = async (
    importCandidateId: string,
    replaceMode: ImportApplyMode,
  ) => {
    const selectedSections = candidateSelections[importCandidateId] ?? [];
    const busyKey = `${importCandidateId}:${replaceMode}`;

    if (replaceMode === "partial_replace" && selectedSections.length === 0) {
      setMutationFeedback("Для выборочной замены нужно отметить хотя бы один раздел.");
      return;
    }

    const isConfirmed = window.confirm(
      replaceMode === "full_replace"
        ? "Полностью заменить текущий draft содержимым import candidate? Перед заменой будет создан backup."
        : `Применить к draft только выбранные разделы (${selectedSections.join(", ")})? Перед заменой будет создан backup.`,
    );

    if (!isConfirmed) {
      return;
    }

    try {
      setBusyImportActionKey(busyKey);
      setMutationFeedback(null);

      if (hasLocalDraftChangesRef.current) {
        await persistCurrentDraft();
      }

      const applyResponse = await applyImportCandidateToDraft(importCandidateId, {
        replaceMode,
        sections: replaceMode === "partial_replace" ? selectedSections : [],
      });

      hasLocalDraftChangesRef.current = false;
      setDraftContent(applyResponse.snapshot.payload);
      await loadDashboardData();
      setMutationFeedback(
        applyResponse.backup
          ? `Import candidate применен (${applyResponse.replaceMode}); предыдущий draft сохранен в backup ${applyResponse.backup.fileName}.`
          : `Import candidate применен (${applyResponse.replaceMode}).`,
      );
    } catch (error) {
      setMutationFeedback(error instanceof Error ? error.message : "Не удалось применить import candidate.");
    } finally {
      setBusyImportActionKey(null);
    }
  };

  const contentStateWarnings = pickStringArray(contentState.sourceMetadata.warnings);
  const contentStateOverrides = pickStringArray(contentState.sourceMetadata.manualOverrides);

  return (
    <div className="admin-shell">
      <header className="admin-hero">
        <div>
          <p className="admin-hero__eyebrow">Admin control room</p>
          <h1 className="admin-hero__title">Панель управления контентом и аналитикой</h1>
          <p className="admin-hero__description">
            Слой уже собран под согласованную архитектуру: один SSR-снимок, staged import
            как control version workflow, backup registry без хранения старых версий в БД,
            обезличенная аналитика и компактный runtime health без обязательной Grafana.
          </p>
        </div>
        <div className="admin-hero__actions">
          <button
            type="button"
            className="admin-button admin-button--primary"
            onClick={() => void handleDraftSave()}
            disabled={isSavingDraft || isPublishingDraft}
          >
            {isSavingDraft ? "Сохраняю draft..." : "Сохранить draft"}
          </button>
          <button
            type="button"
            className="admin-button admin-button--secondary"
            onClick={() => void handleDraftPublish()}
            disabled={isSavingDraft || isPublishingDraft}
          >
            {isPublishingDraft ? "Публикую..." : "Опубликовать draft"}
          </button>
          <button type="button" className="admin-button admin-button--ghost" onClick={handleDraftExport}>
            Выгрузить draft
          </button>
          <label className="admin-button admin-button--secondary">
            Загрузить draft
            <input type="file" accept="application/json" hidden onChange={handleDraftImport} />
          </label>
        </div>
      </header>

      <div className="admin-runtime-note">
        <span className={`admin-runtime-note__badge admin-runtime-note__badge--${dashboardSource}`}>
          {dashboardSource === "live_api" ? "Live API" : "Preview fallback"}
        </span>
        <span className="admin-runtime-note__text">
          {dashboardSource === "live_api"
            ? "Админка читает snapshot, analytics, system state и logs из backend API."
            : "Админка временно показывает встроенные preview-данные до подключения backend API."}
        </span>
      </div>

      {dashboardLoadError ? (
        <div className="admin-runtime-alert">
          <strong>Admin API fallback:</strong> {dashboardLoadError}
        </div>
      ) : null}

      {mutationFeedback ? <div className="admin-runtime-alert">{mutationFeedback}</div> : null}

      <section className="admin-summary-grid">
        <article className="admin-stat-card">
          <span className="admin-stat-card__label">All-time sessions</span>
          <strong className="admin-stat-card__value">{analyticsSnapshot.allTimeTotals.sessions}</strong>
          <span className="admin-stat-card__hint">Daily retention: 548 дней</span>
        </article>
        <article className="admin-stat-card">
          <span className="admin-stat-card__label">All-time section views</span>
          <strong className="admin-stat-card__value">{analyticsSnapshot.allTimeTotals.sectionViews}</strong>
          <span className="admin-stat-card__hint">Daily retention: 365 дней</span>
        </article>
        <article className="admin-stat-card">
          <span className="admin-stat-card__label">All-time section clicks</span>
          <strong className="admin-stat-card__value">{analyticsSnapshot.allTimeTotals.sectionClicks}</strong>
          <span className="admin-stat-card__hint">Daily retention: 365 дней</span>
        </article>
        <article className="admin-stat-card">
          <span className="admin-stat-card__label">Grafana</span>
          <strong className="admin-stat-card__value">
            {runtimeHealth.grafanaEnabled ? "Enabled" : "Fallback mode"}
          </strong>
          <span className="admin-stat-card__hint">Включать только если сервер выдержит</span>
        </article>
      </section>

      <section className="admin-grid">
        <article className="admin-card">
          <h2 className="admin-card__title">Профиль</h2>
          <label className="admin-field">
            <span>Имя (RU)</span>
            <input
              value={draftContent.profile.displayName.ru}
              onChange={(event) => updateProfileField("displayName", "ru", event.target.value)}
            />
          </label>
          <label className="admin-field">
            <span>Имя (EN)</span>
            <input
              value={draftContent.profile.displayName.en}
              onChange={(event) => updateProfileField("displayName", "en", event.target.value)}
            />
          </label>
          <label className="admin-field">
            <span>Заголовок (RU)</span>
            <textarea
              rows={4}
              value={draftContent.profile.headline.ru}
              onChange={(event) => updateProfileField("headline", "ru", event.target.value)}
            />
          </label>
          <label className="admin-field">
            <span>Заголовок (EN)</span>
            <textarea
              rows={4}
              value={draftContent.profile.headline.en}
              onChange={(event) => updateProfileField("headline", "en", event.target.value)}
            />
          </label>
        </article>

        <article className="admin-card">
          <h2 className="admin-card__title">Проект-эталон</h2>
          {canRenderProjectEditor ? (
            <>
              <label className="admin-field">
                <span>Название (RU)</span>
                <input
                  value={firstProject.title.ru}
                  onChange={(event) => updateFirstProjectField("title", "ru", event.target.value)}
                />
              </label>
              <label className="admin-field">
                <span>Название (EN)</span>
                <input
                  value={firstProject.title.en}
                  onChange={(event) => updateFirstProjectField("title", "en", event.target.value)}
                />
              </label>
              <label className="admin-field">
                <span>Описание (RU)</span>
                <textarea
                  rows={6}
                  value={firstProject.summary.ru}
                  onChange={(event) => updateFirstProjectField("summary", "ru", event.target.value)}
                />
              </label>
              <label className="admin-field">
                <span>Описание (EN)</span>
                <textarea
                  rows={6}
                  value={firstProject.summary.en}
                  onChange={(event) => updateFirstProjectField("summary", "en", event.target.value)}
                />
              </label>
            </>
          ) : (
            <p>Проекты ещё не загружены.</p>
          )}
        </article>

        <article className="admin-card">
          <h2 className="admin-card__title">Preview и consent</h2>
          <label className="admin-field">
            <span>Язык предпросмотра</span>
            <select
              value={previewLocale}
              onChange={(event) => setPreviewLocale(event.target.value as "ru" | "en")}
            >
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
          <div className="admin-preview">
            <p className="admin-preview__name">{deferredDraftContent.profile.displayName[previewLocale]}</p>
            <p className="admin-preview__headline">{deferredDraftContent.profile.headline[previewLocale]}</p>
            <p className="admin-preview__summary">{deferredDraftContent.profile.summary[previewLocale]}</p>
          </div>
          <div className="admin-inline-note">
            <strong>{consentContent.modalTitle[previewLocale]}</strong>
            <p>{consentContent.modalBodyMarkdown[previewLocale]}</p>
          </div>
        </article>

        <article className="admin-card admin-card--wide">
          <div className="admin-card__header">
            <div>
              <h2 className="admin-card__title">Аналитика по дням</h2>
              <p className="admin-card__description">
                Графики собираются только из обезличенных агрегатов по сессиям, просмотрам и кликам.
              </p>
            </div>
          </div>
          <div className="admin-chart-grid">
            <div className="admin-chart-card">
              <h3>Sessions</h3>
              <div className="admin-bar-list">
                {analyticsSnapshot.sessionsLast7Days.map((point) => (
                  <div key={`sessions-${point.label}`} className="admin-bar-row">
                    <span className="admin-bar-row__label">{point.label}</span>
                    <div className="admin-bar-row__track">
                      <div
                        className="admin-bar-row__fill"
                        style={{ width: `${(point.value / sessionSeriesMax) * 100}%` }}
                      />
                    </div>
                    <span className="admin-bar-row__value">
                      {point.value}
                      {point.blockedValue ? ` / blocked ${point.blockedValue}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="admin-chart-card">
              <h3>Section views</h3>
              <div className="admin-bar-list">
                {analyticsSnapshot.viewsLast7Days.map((point) => (
                  <div key={`views-${point.label}`} className="admin-bar-row">
                    <span className="admin-bar-row__label">{point.label}</span>
                    <div className="admin-bar-row__track">
                      <div
                        className="admin-bar-row__fill admin-bar-row__fill--views"
                        style={{ width: `${(point.value / viewSeriesMax) * 100}%` }}
                      />
                    </div>
                    <span className="admin-bar-row__value">
                      {point.value}
                      {point.blockedValue ? ` / blocked ${point.blockedValue}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="admin-chart-card">
              <h3>Section clicks</h3>
              <div className="admin-bar-list">
                {analyticsSnapshot.clicksLast7Days.map((point) => (
                  <div key={`clicks-${point.label}`} className="admin-bar-row">
                    <span className="admin-bar-row__label">{point.label}</span>
                    <div className="admin-bar-row__track">
                      <div
                        className="admin-bar-row__fill admin-bar-row__fill--clicks"
                        style={{ width: `${(point.value / clickSeriesMax) * 100}%` }}
                      />
                    </div>
                    <span className="admin-bar-row__value">
                      {point.value}
                      {point.blockedValue ? ` / blocked ${point.blockedValue}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </article>

        <article className="admin-card">
          <h2 className="admin-card__title">Top sections и CTA</h2>
          <div className="admin-ranked-list">
            {analyticsSnapshot.topSections.map((sectionItem) => (
              <div key={sectionItem.key} className="admin-ranked-row">
                <span>{sectionItem.label.ru}</span>
                <strong>{sectionItem.total}</strong>
              </div>
            ))}
          </div>
          <div className="admin-divider" />
          <div className="admin-ranked-list">
            {analyticsSnapshot.topActions.map((actionItem) => (
              <div key={actionItem.key} className="admin-ranked-row">
                <span>{actionItem.label.ru}</span>
                <strong>{actionItem.total}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-card">
          <h2 className="admin-card__title">Content state</h2>
          <div className="admin-meta-list">
            <div className="admin-meta-row">
              <span>State key</span>
              <strong>{contentState.stateKey}</strong>
            </div>
            <div className="admin-meta-row">
              <span>Last import status</span>
              <strong>{contentState.lastImportStatus}</strong>
            </div>
            <div className="admin-meta-row">
              <span>Last imported at</span>
              <strong>{contentState.lastImportedAt ? formatDateTime(contentState.lastImportedAt) : "never"}</strong>
            </div>
            <div className="admin-meta-row">
              <span>Pending candidate</span>
              <strong>{contentState.pendingImportCandidateId ?? "none"}</strong>
            </div>
            <div className="admin-meta-row">
              <span>Current backup</span>
              <strong>{contentState.currentBackupArtifactId ?? "none"}</strong>
            </div>
          </div>
          <div className="admin-chip-list">
            {contentStateWarnings.map((warning) => (
              <span key={warning} className="admin-chip admin-chip--warning">
                {warning}
              </span>
            ))}
            {contentStateOverrides.map((overridePath) => (
              <span key={overridePath} className="admin-chip">
                override: {overridePath}
              </span>
            ))}
          </div>
        </article>

        <article className="admin-card admin-card--wide">
          <div className="admin-card__header">
            <div>
              <h2 className="admin-card__title">Backup registry</h2>
              <p className="admin-card__description">
                Старые версии лежат как экспортируемые bundle-файлы, а не как история в БД.
              </p>
            </div>
            <button
              type="button"
              className="admin-button admin-button--secondary"
              onClick={() => void handleDraftBackupCreate()}
              disabled={isCreatingDraftBackup || isSavingDraft || isPublishingDraft}
            >
              {isCreatingDraftBackup ? "Создаю backup..." : "Создать backup draft"}
            </button>
          </div>
          <div className="admin-table-like">
            {backupArtifacts.map((backupItem) => (
              <div key={backupItem.backupId} className="admin-table-like__row">
                <div>
                  <strong>{backupItem.fileName}</strong>
                  <p>{backupItem.backupKind} • {backupItem.snapshotKind}</p>
                </div>
                <div>
                  <strong>{formatBytes(backupItem.fileSizeBytes)}</strong>
                  <p>{formatDateTime(backupItem.createdAt)}</p>
                </div>
                <div className="admin-row-actions">
                  <button
                    type="button"
                    className="admin-button admin-button--ghost"
                    onClick={() => handleBackupDownload(backupItem.backupId)}
                    disabled={busyBackupId === backupItem.backupId}
                  >
                    Скачать
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button--ghost"
                    onClick={() => void handleBackupCompare(backupItem.backupId)}
                    disabled={busyDiffKey === `backup:${backupItem.backupId}`}
                  >
                    {busyDiffKey === `backup:${backupItem.backupId}` ? "Сравниваю..." : "Сравнить"}
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button--ghost-danger"
                    onClick={() => void handleBackupDelete(backupItem.backupId)}
                    disabled={busyBackupId === backupItem.backupId}
                  >
                    {busyBackupId === backupItem.backupId ? "Удаляю..." : "Удалить"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-card admin-card--wide">
          <div className="admin-card__header">
            <div>
              <h2 className="admin-card__title">Import control version</h2>
              <p className="admin-card__description">
                Импорт работает как staged review: можно сравнить с draft или backup, затем применить
                полностью или выборочно по разделам.
              </p>
            </div>
            <label className="admin-button admin-button--secondary">
              {isUploadingImportCandidate ? "Загружаю candidate..." : "Загрузить candidate"}
              <input
                type="file"
                accept="application/json"
                hidden
                disabled={isUploadingImportCandidate || Boolean(busyImportActionKey)}
                onChange={handleImportCandidateUpload}
              />
            </label>
          </div>

          {currentDiff ? (
            <div className="admin-diff-card">
              <div className="admin-meta-list">
                <div className="admin-meta-row">
                  <span>Left</span>
                  <strong>{currentDiff.leftLabel}</strong>
                </div>
                <div className="admin-meta-row">
                  <span>Right</span>
                  <strong>{currentDiff.rightLabel}</strong>
                </div>
                <div className="admin-meta-row">
                  <span>Changed paths</span>
                  <strong>{currentDiff.summary.changedPathsCount}</strong>
                </div>
                <div className="admin-meta-row">
                  <span>Changed sections</span>
                  <strong>{currentDiff.summary.sectionsChangedCount}</strong>
                </div>
              </div>
              <div className="admin-chip-list">
                {currentDiff.sections.map((sectionName) => (
                  <span key={sectionName} className="admin-chip admin-chip--warning">
                    {sectionName}
                  </span>
                ))}
              </div>
              <div className="admin-diff-path-list">
                {currentDiff.changedPaths.slice(0, 12).map((changedPath) => (
                  <code key={changedPath} className="admin-diff-path">
                    {changedPath}
                  </code>
                ))}
              </div>
              {currentDiff.changedPaths.length > 12 ? (
                <p className="admin-card__description">
                  Показаны первые 12 путей из {currentDiff.changedPaths.length}.
                </p>
              ) : null}
            </div>
          ) : null}

          {importCandidates.length === 0 ? (
            <p className="admin-card__description">
              Пока нет staged import-кандидатов. Загрузите export/import bundle, чтобы открыть review workflow.
            </p>
          ) : null}

          {importCandidates.map((candidateItem) => {
            const selectedSections = candidateSelections[candidateItem.importCandidateId] ?? [];
            const draftCompareKey = `candidate-draft:${candidateItem.importCandidateId}`;
            const backupCompareKey = `candidate-backup:${candidateItem.importCandidateId}`;
            const partialApplyKey = `${candidateItem.importCandidateId}:partial_replace`;
            const fullApplyKey = `${candidateItem.importCandidateId}:full_replace`;

            return (
              <div key={candidateItem.importCandidateId} className="admin-import-card">
                <div className="admin-meta-list">
                  <div className="admin-meta-row">
                    <span>Candidate</span>
                    <strong>{candidateItem.importCandidateId}</strong>
                  </div>
                  <div className="admin-meta-row">
                    <span>Status</span>
                    <strong>{candidateItem.parseStatus}</strong>
                  </div>
                  <div className="admin-meta-row">
                    <span>Created</span>
                    <strong>{formatDateTime(candidateItem.createdAt)}</strong>
                  </div>
                  <div className="admin-meta-row">
                    <span>Warnings</span>
                    <strong>{candidateItem.reviewSummary.warningsCount}</strong>
                  </div>
                  <div className="admin-meta-row">
                    <span>Can replace fully</span>
                    <strong>{candidateItem.reviewSummary.canReplaceFully ? "yes" : "no"}</strong>
                  </div>
                </div>
                <div className="admin-chip-list">
                  {candidateItem.reviewSummary.replaceableSections.map((sectionName) => {
                    const isSelected = selectedSections.includes(sectionName);

                    return (
                      <button
                        key={sectionName}
                        type="button"
                        className={`admin-chip admin-chip--toggle${isSelected ? " admin-chip--selected" : ""}`}
                        onClick={() => toggleCandidateSection(candidateItem.importCandidateId, sectionName)}
                      >
                        {sectionName}
                      </button>
                    );
                  })}
                </div>
                <p className="admin-card__description">
                  Для partial replace выбрано: {selectedSections.length > 0 ? selectedSections.join(", ") : "ничего"}.
                </p>
                <div className="admin-row-actions">
                  <button
                    type="button"
                    className="admin-button admin-button--secondary"
                    onClick={() => void handleImportCandidateCompareToDraft(candidateItem.importCandidateId)}
                    disabled={busyDiffKey === draftCompareKey}
                  >
                    {busyDiffKey === draftCompareKey ? "Сравниваю..." : "Сравнить с draft"}
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button--secondary"
                    onClick={() => void handleImportCandidateCompareToBackup(candidateItem.importCandidateId)}
                    disabled={busyDiffKey === backupCompareKey}
                  >
                    {busyDiffKey === backupCompareKey ? "Сравниваю..." : "Сравнить с backup"}
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button--primary"
                    onClick={() => void handleImportCandidateApply(candidateItem.importCandidateId, "partial_replace")}
                    disabled={busyImportActionKey === fullApplyKey || busyImportActionKey === partialApplyKey}
                  >
                    {busyImportActionKey === partialApplyKey ? "Применяю..." : "Подтверждаю выборочную замену"}
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button--ghost"
                    onClick={() => void handleImportCandidateApply(candidateItem.importCandidateId, "full_replace")}
                    disabled={
                      !candidateItem.reviewSummary.canReplaceFully ||
                      busyImportActionKey === fullApplyKey ||
                      busyImportActionKey === partialApplyKey
                    }
                  >
                    {busyImportActionKey === fullApplyKey ? "Заменяю..." : "Полностью заменить"}
                  </button>
                </div>
              </div>
            );
          })}
        </article>

        <article className="admin-card">
          <h2 className="admin-card__title">Runtime health</h2>
          <div className="admin-service-grid">
            {Object.entries(runtimeHealth.services).map(([serviceName, serviceState]) => (
              <div key={serviceName} className={`admin-service-pill admin-service-pill--${serviceState}`}>
                <span>{serviceName}</span>
                <strong>{serviceState}</strong>
              </div>
            ))}
          </div>
          <div className="admin-meta-list">
            <div className="admin-meta-row">
              <span>Source</span>
              <strong>{runtimeHealth.sourceKind}</strong>
            </div>
            <div className="admin-meta-row">
              <span>Disk free</span>
              <strong>{runtimeHealth.diskFreeMb} MB</strong>
            </div>
            <div className="admin-meta-row">
              <span>Memory pressure</span>
              <strong>{runtimeHealth.memoryPressure}</strong>
            </div>
            <div className="admin-meta-row">
              <span>Snapshot updated</span>
              <strong>{formatDateTime(runtimeHealth.updatedAt)}</strong>
            </div>
          </div>
        </article>

        <article className="admin-card">
          <h2 className="admin-card__title">Recent audit log</h2>
          <div className="admin-log-list">
            {auditLogs.map((logItem) => (
              <div key={logItem.logId} className="admin-log-row">
                <div>
                  <strong>{logItem.actionCode}</strong>
                  <p>{logItem.entityType} • {logItem.entityKey ?? "n/a"}</p>
                </div>
                <div>
                  <strong>{logItem.resultCode}</strong>
                  <p>{formatDateTime(logItem.occurredAt)}</p>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
