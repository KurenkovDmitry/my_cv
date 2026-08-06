import { ChangeEvent, useMemo, useState } from "react";
import type { ContentAssetSummary, PortfolioContent } from "@portfolio/shared-types";

type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
interface JsonObject {
  [fieldName: string]: JsonValue;
}
type JsonPath = Array<string | number>;

interface PortfolioContentEditorProps {
  content: PortfolioContent;
  assets: ContentAssetSummary[];
  onChange: (nextContent: PortfolioContent) => void;
  onUploadAsset: (file: File) => Promise<ContentAssetSummary>;
  onDeleteAsset: (assetId: string) => Promise<void>;
}

interface JsonValueEditorProps {
  value: JsonValue;
  path: JsonPath;
  label: string;
  assets: ContentAssetSummary[];
  onReplace: (path: JsonPath, nextValue: JsonValue) => void;
  onRemove: (path: JsonPath) => void;
  onMove: (path: JsonPath, direction: -1 | 1) => void;
  onUploadAsset: (file: File) => Promise<ContentAssetSummary>;
}

const ROOT_SECTION_KEYS: Array<keyof PortfolioContent> = [
  "profile",
  "experience",
  "projects",
  "education",
  "skills",
  "themes",
  "localization",
  "accessibility",
  "legal",
  "seo",
  "version",
  "draft",
  "needsManualReview",
  "contentAssetsVersion",
];

const FIELD_LABELS: Record<string, string> = {
  profile: "Профиль и контакты",
  experience: "Опыт работы",
  projects: "Проекты",
  education: "Образование",
  skills: "Компетенции и подтверждения",
  themes: "Темы оформления",
  localization: "Языки и регионы",
  accessibility: "Доступность",
  legal: "Согласия и юридический текст",
  seo: "SEO и карточка ссылки",
  version: "Версия модели",
  draft: "Черновик",
  needsManualReview: "Нужна ручная проверка",
  contentAssetsVersion: "Версия файлового контура",
  slug: "Системный slug",
  displayName: "Имя",
  headline: "Профессиональный заголовок",
  summary: "Описание",
  location: "Местоположение",
  avatarAsset: "Резервный URL фотографии",
  avatarAssetId: "Фотография",
  availability: "Статус доступности",
  contacts: "Контакты",
  kind: "Тип",
  label: "Подпись",
  value: "Значение",
  href: "Ссылка",
  id: "Идентификатор",
  company: "Компания",
  role: "Роль",
  period: "Период",
  description: "Описание",
  highlights: "Основные результаты",
  status: "Статус",
  featured: "Выделить проект",
  title: "Название",
  category: "Категория",
  teamSize: "Размер команды",
  responsibilities: "Зона ответственности",
  achievements: "Достижения",
  technologies: "Технологии",
  links: "Ссылки",
  coverAssetId: "Обложка проекта",
  programme: "Программа",
  detail: "Подробности",
  proofId: "ID подтверждения",
  focusAreas: "Ключевые компетенции",
  groups: "Группы навыков",
  items: "Элементы",
  proofs: "Сертификаты, дипломы и подтверждения",
  proofNote: "Примечание к подтверждениям",
  skill: "Подтверждаемый навык",
  level: "Уровень",
  issuer: "Организация",
  issuedAt: "Дата выдачи",
  validUntil: "Действительно до",
  assetHref: "Резервная внешняя ссылка",
  assetId: "Прикреплённый файл",
  note: "Примечание",
  active: "Активная тема",
  available: "Доступные варианты",
  defaultLocale: "Язык по умолчанию",
  supportedLocales: "Поддерживаемые языки",
  autoDetectByRegion: "Определение языка по региону",
  speechSynthesisEnabled: "Озвучивание",
  highContrastModeEnabled: "Высокая контрастность",
  reducedMotionPresetEnabled: "Режим без анимаций",
  analyticsConsent: "Согласие на аналитику",
  modalTitle: "Заголовок окна",
  modalBodyMarkdown: "Текст окна",
  acceptButtonLabel: "Кнопка согласия",
  rejectButtonLabel: "Кнопка отказа",
  siteName: "Название сайта",
  openGraphImage: "Резервное изображение Open Graph",
  openGraphAssetId: "Изображение карточки ссылки",
  ru: "Русский",
  en: "Английский",
};

const ENUM_OPTIONS: Record<string, string[]> = {
  "profile.contacts.kind": ["email", "phone", "github", "telegram", "social"],
  "experience.status": ["published", "needs_review"],
  "projects.status": ["active", "archived", "draft"],
  "projects.category": ["commercial", "academic", "hackathon"],
  "projects.links.kind": ["repository", "case-study", "demo"],
  "education.status": ["draft", "published", "needs_review"],
  "skills.proofs.kind": ["certificate", "diploma", "registration", "recommendation"],
  "localization.defaultLocale": ["ru", "en"],
};

const LONG_TEXT_FIELDS = new Set([
  "summary",
  "description",
  "detail",
  "note",
  "proofNote",
  "modalBodyMarkdown",
]);

/**
 * Полный редактор переносимой модели `portfolio.v1`.
 *
 * Форма строится рекурсивно, поэтому новые поля snapshot становятся редактируемыми
 * сразу после появления в контракте. Для частых сущностей используются безопасные
 * шаблоны добавления, а advanced JSON остаётся аварийным способом изменить всю модель.
 */
export function PortfolioContentEditor({
  content,
  assets,
  onChange,
  onUploadAsset,
  onDeleteAsset,
}: PortfolioContentEditorProps) {
  const [activeSection, setActiveSection] = useState<keyof PortfolioContent>("profile");
  const [isJsonEditorVisible, setIsJsonEditorVisible] = useState(false);
  const [jsonDraft, setJsonDraft] = useState(() => JSON.stringify(content, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);

  const jsonContent = content as unknown as JsonObject;
  const activeValue = jsonContent[activeSection] ?? null;
  const referencedAssetIds = useMemo(() => collectAssetIds(jsonContent), [content]);

  const replaceValue = (path: JsonPath, nextValue: JsonValue) => {
    onChange(mutateJsonContent(content, path, (container, fieldName) => {
      if (Array.isArray(container) && typeof fieldName === "number") {
        container[fieldName] = nextValue;
      } else if (!Array.isArray(container) && typeof fieldName === "string") {
        container[fieldName] = nextValue;
      }
    }));
  };

  const removeValue = (path: JsonPath) => {
    onChange(mutateJsonContent(content, path, (container, fieldName) => {
      if (Array.isArray(container) && typeof fieldName === "number") {
        container.splice(fieldName, 1);
      } else if (!Array.isArray(container) && typeof fieldName === "string") {
        delete container[fieldName];
      }
    }));
  };

  const moveValue = (path: JsonPath, direction: -1 | 1) => {
    onChange(mutateJsonContent(content, path, (container, fieldName) => {
      if (!Array.isArray(container) || typeof fieldName !== "number") {
        return;
      }
      const targetIndex = fieldName + direction;
      if (targetIndex < 0 || targetIndex >= container.length) {
        return;
      }
      [container[fieldName], container[targetIndex]] = [container[targetIndex], container[fieldName]];
    }));
  };

  const applyJsonDraft = () => {
    try {
      const parsedContent = JSON.parse(jsonDraft) as PortfolioContent;
      if (parsedContent.version !== "portfolio.v1") {
        throw new Error("Корневое поле version должно быть равно portfolio.v1.");
      }
      onChange(parsedContent);
      setJsonError(null);
    } catch (error) {
      setJsonError(error instanceof Error ? error.message : "JSON не удалось разобрать.");
    }
  };

  const handleAssetDelete = async (assetId: string) => {
    if (referencedAssetIds.has(assetId)) {
      window.alert("Сначала удалите ссылки на этот файл из профиля, проекта, SEO или подтверждения навыка.");
      return;
    }
    if (!window.confirm("Физически удалить этот файл? Операцию нельзя отменить без backup.")) {
      return;
    }
    await onDeleteAsset(assetId);
  };

  return (
    <section className="content-editor">
      <div className="content-editor__header">
        <div>
          <p className="content-editor__eyebrow">Полный snapshot editor</p>
          <h2 className="content-editor__title">Вся информация сайта без изменения кода</h2>
          <p className="content-editor__description">
            Изменения остаются локальным draft, пока вы не нажмёте «Сохранить» и «Опубликовать».
          </p>
        </div>
        <button
          type="button"
          className="admin-button admin-button--ghost"
          onClick={() => {
            setJsonDraft(JSON.stringify(content, null, 2));
            setIsJsonEditorVisible((currentValue) => !currentValue);
            setJsonError(null);
          }}
        >
          {isJsonEditorVisible ? "Закрыть JSON" : "Advanced JSON"}
        </button>
      </div>

      {isJsonEditorVisible ? (
        <div className="content-editor__json-panel">
          <textarea
            className="content-editor__json-input"
            spellCheck={false}
            value={jsonDraft}
            onChange={(event) => setJsonDraft(event.target.value)}
          />
          {jsonError ? <p className="content-editor__error">{jsonError}</p> : null}
          <div className="admin-row-actions">
            <button type="button" className="admin-button admin-button--primary" onClick={applyJsonDraft}>
              Применить JSON к draft
            </button>
            <button
              type="button"
              className="admin-button admin-button--ghost"
              onClick={() => setJsonDraft(JSON.stringify(content, null, 2))}
            >
              Вернуть данные формы
            </button>
          </div>
        </div>
      ) : (
        <>
          <nav className="content-editor__tabs" aria-label="Разделы резюме">
            {ROOT_SECTION_KEYS.map((sectionKey) => (
              <button
                key={sectionKey}
                type="button"
                className={`content-editor__tab${activeSection === sectionKey ? " content-editor__tab--active" : ""}`}
                onClick={() => setActiveSection(sectionKey)}
              >
                {getFieldLabel(sectionKey)}
                {Array.isArray(jsonContent[sectionKey]) ? (
                  <span>{(jsonContent[sectionKey] as JsonValue[]).length}</span>
                ) : null}
              </button>
            ))}
          </nav>
          <div className="content-editor__workspace">
            <JsonValueEditor
              value={activeValue}
              path={[activeSection]}
              label={getFieldLabel(activeSection)}
              assets={assets}
              onReplace={replaceValue}
              onRemove={removeValue}
              onMove={moveValue}
              onUploadAsset={onUploadAsset}
            />
          </div>
        </>
      )}

      <details className="content-editor__asset-registry">
        <summary>Файловый реестр · {assets.length}</summary>
        <div className="content-editor__asset-list">
          {assets.length === 0 ? <p>Загруженных через админку файлов пока нет.</p> : null}
          {assets.map((assetItem) => (
            <article key={assetItem.assetId} className="content-editor__asset-row">
              <div>
                <strong>{assetItem.fileName}</strong>
                <p>{assetItem.mediaType} · {formatBytes(assetItem.fileSizeBytes)}</p>
              </div>
              <span>{referencedAssetIds.has(assetItem.assetId) ? "используется" : "не прикреплён"}</span>
              <button
                type="button"
                className="admin-button admin-button--ghost"
                onClick={() => void handleAssetDelete(assetItem.assetId)}
              >
                Удалить
              </button>
            </article>
          ))}
        </div>
      </details>
    </section>
  );
}

/** Рекурсивно отображает один узел JSON-модели с операциями над массивами и объектами. */
function JsonValueEditor({
  value,
  path,
  label,
  assets,
  onReplace,
  onRemove,
  onMove,
  onUploadAsset,
}: JsonValueEditorProps) {
  const fieldName = String(path.at(-1) ?? "");
  const normalizedPath = normalizePath(path);

  if (Array.isArray(value)) {
    return (
      <div className="content-field content-field--collection">
        <div className="content-field__heading">
          <div>
            <strong>{label}</strong>
            <span>{value.length} элементов</span>
          </div>
          <button
            type="button"
            className="admin-button admin-button--secondary"
            onClick={() => onReplace(path, [...value, createArrayItem(path, value)])}
          >
            + Добавить
          </button>
        </div>
        <div className="content-collection">
          {value.length === 0 ? <p className="content-collection__empty">Список пуст. Добавьте первый элемент.</p> : null}
          {value.map((arrayItem, itemIndex) => {
            const itemPath = [...path, itemIndex];
            return (
              <details key={`${normalizedPath}-${itemIndex}`} className="content-collection__item" open={value.length < 4}>
                <summary>
                  <span>{getItemTitle(arrayItem, itemIndex)}</span>
                  <span className="content-collection__summary-actions" onClick={(event) => event.preventDefault()}>
                    <button type="button" onClick={() => onMove(itemPath, -1)} disabled={itemIndex === 0}>↑</button>
                    <button type="button" onClick={() => onMove(itemPath, 1)} disabled={itemIndex === value.length - 1}>↓</button>
                    <button type="button" onClick={() => onRemove(itemPath)}>Удалить</button>
                  </span>
                </summary>
                <JsonValueEditor
                  value={arrayItem}
                  path={itemPath}
                  label={`${label} ${itemIndex + 1}`}
                  assets={assets}
                  onReplace={onReplace}
                  onRemove={onRemove}
                  onMove={onMove}
                  onUploadAsset={onUploadAsset}
                />
              </details>
            );
          })}
        </div>
      </div>
    );
  }

  if (isJsonObject(value)) {
    const attachmentFieldName = resolveAttachmentFieldName(path);
    return (
      <fieldset className="content-field content-field--object">
        <legend>{label}</legend>
        {attachmentFieldName ? (
          <AssetPicker
            fieldLabel={getFieldLabel(attachmentFieldName)}
            assetId={typeof value[attachmentFieldName] === "string" ? value[attachmentFieldName] : ""}
            assets={assets}
            onChange={(nextAssetId) => {
              const attachmentPath = [...path, attachmentFieldName];
              if (nextAssetId) onReplace(attachmentPath, nextAssetId);
              else onRemove(attachmentPath);
            }}
            onUploadAsset={onUploadAsset}
          />
        ) : null}
        <div className="content-field__object-grid">
          {Object.entries(value).map(([nestedFieldName, nestedValue]) => {
            if (nestedFieldName === attachmentFieldName) {
              return null;
            }
            return (
              <JsonValueEditor
                key={`${normalizedPath}.${nestedFieldName}`}
                value={nestedValue}
                path={[...path, nestedFieldName]}
                label={getFieldLabel(nestedFieldName)}
                assets={assets}
                onReplace={onReplace}
                onRemove={onRemove}
                onMove={onMove}
                onUploadAsset={onUploadAsset}
              />
            );
          })}
        </div>
      </fieldset>
    );
  }

  if (typeof value === "boolean") {
    return (
      <label className="content-field content-field--boolean">
        <input type="checkbox" checked={value} onChange={(event) => onReplace(path, event.target.checked)} />
        <span>{label}</span>
      </label>
    );
  }

  if (typeof value === "number") {
    return (
      <label className="content-field">
        <span>{label}</span>
        <input type="number" value={value} onChange={(event) => onReplace(path, Number(event.target.value))} />
      </label>
    );
  }

  const stringValue = value === null ? "" : String(value);
  const enumOptions = findEnumOptions(path);
  if (enumOptions) {
    return (
      <label className="content-field">
        <span>{label}</span>
        <select value={stringValue} onChange={(event) => onReplace(path, event.target.value)}>
          {enumOptions.map((enumValue) => <option key={enumValue} value={enumValue}>{enumValue}</option>)}
        </select>
      </label>
    );
  }

  if (LONG_TEXT_FIELDS.has(fieldName) || stringValue.length > 120) {
    return (
      <label className="content-field content-field--wide">
        <span>{label}</span>
        <textarea rows={5} value={stringValue} onChange={(event) => onReplace(path, event.target.value)} />
      </label>
    );
  }

  return (
    <label className="content-field">
      <span>{label}</span>
      <input
        type={fieldName === "issuedAt" || fieldName === "validUntil" ? "date" : "text"}
        value={stringValue}
        onChange={(event) => onReplace(path, event.target.value)}
      />
    </label>
  );
}

interface AssetPickerProps {
  fieldLabel: string;
  assetId: string;
  assets: ContentAssetSummary[];
  onChange: (assetId: string) => void;
  onUploadAsset: (file: File) => Promise<ContentAssetSummary>;
}

/** Позволяет выбрать ранее загруженный файл или безопасно загрузить новый. */
function AssetPicker({ fieldLabel, assetId, assets, onChange, onUploadAsset }: AssetPickerProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      return;
    }
    try {
      setIsUploading(true);
      setUploadError(null);
      const uploadedAsset = await onUploadAsset(selectedFile);
      onChange(uploadedAsset.assetId);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Файл не удалось загрузить.");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  return (
    <div className="asset-picker">
      <label className="content-field">
        <span>{fieldLabel}</span>
        <select value={assetId} onChange={(event) => onChange(event.target.value)}>
          <option value="">Не прикреплён</option>
          {assets.map((assetItem) => (
            <option key={assetItem.assetId} value={assetItem.assetId}>{assetItem.fileName}</option>
          ))}
        </select>
      </label>
      <label className="admin-button admin-button--secondary asset-picker__upload">
        {isUploading ? "Загрузка..." : "Загрузить PDF или изображение"}
        <input
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/webp"
          hidden
          disabled={isUploading}
          onChange={(event) => void handleUpload(event)}
        />
      </label>
      {uploadError ? <p className="content-editor__error">{uploadError}</p> : null}
    </div>
  );
}

/** Создаёт независимую копию snapshot и применяет одну точечную мутацию. */
function mutateJsonContent(
  content: PortfolioContent,
  path: JsonPath,
  mutation: (container: JsonObject | JsonValue[], fieldName: string | number) => void,
): PortfolioContent {
  const clonedContent = structuredClone(content) as unknown as JsonObject;
  if (path.length === 0) {
    return clonedContent as unknown as PortfolioContent;
  }
  let currentContainer: JsonValue = clonedContent;
  for (const pathPart of path.slice(0, -1)) {
    if (Array.isArray(currentContainer) && typeof pathPart === "number") {
      currentContainer = currentContainer[pathPart];
    } else if (isJsonObject(currentContainer) && typeof pathPart === "string") {
      currentContainer = currentContainer[pathPart];
    } else {
      throw new Error(`Не удалось найти поле ${normalizePath(path)}.`);
    }
  }
  if (!Array.isArray(currentContainer) && !isJsonObject(currentContainer)) {
    throw new Error(`Поле ${normalizePath(path)} не имеет изменяемого контейнера.`);
  }
  mutation(currentContainer, path.at(-1) as string | number);
  return clonedContent as unknown as PortfolioContent;
}

/** Возвращает безопасный шаблон для каждой добавляемой сущности резюме. */
function createArrayItem(path: JsonPath, currentItems: JsonValue[]): JsonValue {
  const pathKey = normalizePath(path);
  const localizedText = (): JsonObject => ({ ru: "", en: "" });
  const entityId = (prefix: string) => `${prefix}-${crypto.randomUUID().slice(0, 8)}`;

  if (pathKey === "profile.contacts") return { kind: "email", label: "", value: "", href: "" };
  if (pathKey === "experience") return { id: entityId("experience"), company: localizedText(), role: localizedText(), period: localizedText(), description: localizedText(), highlights: [], status: "published" };
  if (pathKey === "projects") return { id: entityId("project"), slug: entityId("project"), featured: false, status: "draft", title: localizedText(), summary: localizedText(), category: "commercial", period: localizedText(), role: localizedText(), teamSize: 1, responsibilities: [], achievements: [], technologies: [], links: [] };
  if (pathKey === "education") return { id: entityId("education"), title: localizedText(), programme: localizedText(), period: localizedText(), detail: localizedText(), proofId: "", status: "draft" };
  if (pathKey === "skills.groups") return { id: entityId("skill-group"), title: localizedText(), items: [] };
  if (pathKey === "skills.proofs") return { id: entityId("proof"), skill: "", kind: "certificate", title: localizedText(), level: localizedText(), issuer: localizedText(), issuedAt: "", validUntil: "", assetHref: "", note: localizedText() };
  if (pathKey === "themes.available") return { id: entityId("theme"), label: localizedText() };
  if (pathKey.endsWith(".responsibilities") || pathKey.endsWith(".achievements") || pathKey.endsWith(".highlights") || pathKey.endsWith(".items")) return localizedText();
  if (pathKey.endsWith(".links")) return { kind: "repository", label: localizedText(), href: "" };
  if (currentItems.length > 0) return createEmptyShape(currentItems[0]);
  return "";
}

/** Очищает значения существующей формы, сохраняя её расширяемую структуру. */
function createEmptyShape(value: JsonValue): JsonValue {
  if (Array.isArray(value)) return [];
  if (isJsonObject(value)) return Object.fromEntries(Object.entries(value).map(([key, nestedValue]) => [key, createEmptyShape(nestedValue)]));
  if (typeof value === "boolean") return false;
  if (typeof value === "number") return 0;
  if (value === null) return null;
  return "";
}

function resolveAttachmentFieldName(path: JsonPath): string | null {
  const pathKey = normalizePath(path);
  if (pathKey === "profile") return "avatarAssetId";
  if (pathKey === "seo") return "openGraphAssetId";
  if (/^projects\.\d+$/.test(pathKey)) return "coverAssetId";
  if (/^education\.\d+$/.test(pathKey)) return "assetId";
  if (/^skills\.proofs\.\d+$/.test(pathKey)) return "assetId";
  return null;
}

function findEnumOptions(path: JsonPath): string[] | null {
  const normalizedPath = normalizePath(path).replace(/\.\d+/g, "");
  const configuredOptions = ENUM_OPTIONS[normalizedPath];
  if (configuredOptions) return configuredOptions;
  const fieldName = String(path.at(-1));
  if (fieldName === "defaultLocale") return ["ru", "en"];
  return null;
}

function normalizePath(path: JsonPath): string {
  return path.map(String).join(".");
}

function getFieldLabel(fieldName: string): string {
  return FIELD_LABELS[fieldName] ?? fieldName;
}

function getItemTitle(value: JsonValue, itemIndex: number): string {
  if (typeof value === "string") return value || `Элемент ${itemIndex + 1}`;
  if (isJsonObject(value)) {
    for (const preferredField of ["title", "company", "skill", "label", "id"]) {
      const fieldValue = value[preferredField];
      if (typeof fieldValue === "string" && fieldValue) return fieldValue;
      if (isJsonObject(fieldValue) && typeof fieldValue.ru === "string" && fieldValue.ru) return fieldValue.ru;
    }
  }
  return `Элемент ${itemIndex + 1}`;
}

function collectAssetIds(value: JsonValue): Set<string> {
  const assetIds = new Set<string>();
  const visit = (nestedValue: JsonValue, fieldName = "") => {
    if (typeof nestedValue === "string" && fieldName.toLowerCase().endsWith("assetid") && nestedValue) assetIds.add(nestedValue);
    if (Array.isArray(nestedValue)) nestedValue.forEach((arrayItem) => visit(arrayItem));
    if (isJsonObject(nestedValue)) Object.entries(nestedValue).forEach(([key, objectValue]) => visit(objectValue, key));
  };
  visit(value);
  return assetIds;
}

function isJsonObject(value: JsonValue | undefined): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}
