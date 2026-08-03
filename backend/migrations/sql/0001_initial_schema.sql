CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS system;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS public.portfolio_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_kind text NOT NULL,
  content_schema_version text NOT NULL,
  content_json jsonb NOT NULL,
  content_checksum_sha256 text NOT NULL,
  published_locale_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_active boolean NOT NULL DEFAULT false,
  published_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_portfolio_snapshot_snapshot_kind UNIQUE (snapshot_kind),
  CONSTRAINT ck_portfolio_snapshot_published_locale_codes_array
    CHECK (jsonb_typeof(published_locale_codes) = 'array')
);

COMMENT ON TABLE public.portfolio_snapshot IS
'Актуальный контентный слепок сайта. Используется для SSR, preview и экспорта.';
COMMENT ON COLUMN public.portfolio_snapshot.id IS
'Технический первичный ключ записи слепка.';
COMMENT ON COLUMN public.portfolio_snapshot.snapshot_kind IS
'Тип слепка: published или draft.';
COMMENT ON COLUMN public.portfolio_snapshot.content_schema_version IS
'Версия схемы контента внутри content_json.';
COMMENT ON COLUMN public.portfolio_snapshot.content_json IS
'Полный актуальный контент сайта в jsonb для частого чтения без join.';
COMMENT ON COLUMN public.portfolio_snapshot.content_checksum_sha256 IS
'Контрольная сумма слепка для ETag, целостности и инвалидирования кэша.';
COMMENT ON COLUMN public.portfolio_snapshot.published_locale_codes IS
'Компактный список реально опубликованных локалей.';
COMMENT ON COLUMN public.portfolio_snapshot.is_active IS
'Флаг активного слепка для безопасного переключения runtime-состояния.';
COMMENT ON COLUMN public.portfolio_snapshot.published_at IS
'Момент публикации текущего слепка.';
COMMENT ON COLUMN public.portfolio_snapshot.created_at IS
'Время создания строки слепка.';
COMMENT ON COLUMN public.portfolio_snapshot.updated_at IS
'Время последнего изменения слепка.';

CREATE INDEX IF NOT EXISTS ix_portfolio_snapshot_is_active_snapshot_kind
  ON public.portfolio_snapshot (is_active, snapshot_kind);

CREATE TABLE IF NOT EXISTS public.media_asset (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_kind text NOT NULL,
  storage_disk text NOT NULL DEFAULT 'local',
  storage_path text NOT NULL,
  public_url text NULL,
  mime_type text NOT NULL,
  original_filename text NULL,
  file_size_bytes bigint NOT NULL CHECK (file_size_bytes >= 0),
  checksum_sha256 text NOT NULL,
  image_metadata_json jsonb NULL,
  alt_json jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_media_asset_storage_path UNIQUE (storage_path),
  CONSTRAINT uq_media_asset_checksum_sha256 UNIQUE (checksum_sha256)
);

COMMENT ON TABLE public.media_asset IS
'Единый реестр файлов и медиа с минимальным набором метаданных.';
COMMENT ON COLUMN public.media_asset.id IS
'Стабильный идентификатор ассета.';
COMMENT ON COLUMN public.media_asset.asset_kind IS
'Тип ассета: avatar, project_cover, resume_source, open_graph_image и другие.';
COMMENT ON COLUMN public.media_asset.storage_disk IS
'Тип хранилища файла, например local или object-storage.';
COMMENT ON COLUMN public.media_asset.storage_path IS
'Путь к файлу внутри выбранного хранилища.';
COMMENT ON COLUMN public.media_asset.public_url IS
'Готовая публичная ссылка, если файл уже доступен напрямую.';
COMMENT ON COLUMN public.media_asset.mime_type IS
'MIME-тип файла для безопасной отдачи и валидации.';
COMMENT ON COLUMN public.media_asset.original_filename IS
'Исходное имя загруженного файла для админки и диагностики.';
COMMENT ON COLUMN public.media_asset.file_size_bytes IS
'Размер файла в байтах для контроля лимитов сервера.';
COMMENT ON COLUMN public.media_asset.checksum_sha256 IS
'Контрольная сумма файла для дедупликации и целостности.';
COMMENT ON COLUMN public.media_asset.image_metadata_json IS
'Необязательные метаданные изображения: размеры, цвета и другие свойства.';
COMMENT ON COLUMN public.media_asset.alt_json IS
'Локализованные alt-тексты без вынесения в отдельные таблицы.';
COMMENT ON COLUMN public.media_asset.created_at IS
'Время регистрации ассета.';
COMMENT ON COLUMN public.media_asset.updated_at IS
'Время последнего обновления метаданных ассета.';

CREATE INDEX IF NOT EXISTS ix_media_asset_asset_kind
  ON public.media_asset (asset_kind);

CREATE TABLE IF NOT EXISTS system.backup_artifact (
  backup_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  backup_kind text NOT NULL DEFAULT 'export_bundle',
  storage_disk text NOT NULL DEFAULT 'local',
  storage_path text NOT NULL,
  file_size_bytes bigint NOT NULL CHECK (file_size_bytes >= 0),
  checksum_sha256 text NOT NULL,
  content_schema_version text NOT NULL,
  snapshot_kind text NOT NULL,
  snapshot_checksum_sha256 text NOT NULL,
  source_resume_asset_id uuid NULL REFERENCES public.media_asset (id) ON DELETE SET NULL,
  backup_metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by_actor text NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_backup_artifact_storage_path UNIQUE (storage_path),
  CONSTRAINT uq_backup_artifact_checksum_sha256 UNIQUE (checksum_sha256)
);

COMMENT ON TABLE system.backup_artifact IS
'Реестр backup/export-файлов для скачивания, сравнения и обратного импорта.';
COMMENT ON COLUMN system.backup_artifact.backup_id IS
'Первичный ключ backup-артефакта.';
COMMENT ON COLUMN system.backup_artifact.backup_kind IS
'Тип backup-файла: export_bundle, pre_replace_backup, manual_backup.';
COMMENT ON COLUMN system.backup_artifact.storage_disk IS
'Тип хранилища backup-файла.';
COMMENT ON COLUMN system.backup_artifact.storage_path IS
'Путь к backup-файлу для скачивания, сравнения и импорта.';
COMMENT ON COLUMN system.backup_artifact.file_size_bytes IS
'Размер backup-артефакта в байтах.';
COMMENT ON COLUMN system.backup_artifact.checksum_sha256 IS
'Контрольная сумма backup-файла для проверки целостности.';
COMMENT ON COLUMN system.backup_artifact.content_schema_version IS
'Версия формата export/import bundle.';
COMMENT ON COLUMN system.backup_artifact.snapshot_kind IS
'Состояние слепка, из которого создан backup: draft, published, before_replace.';
COMMENT ON COLUMN system.backup_artifact.snapshot_checksum_sha256 IS
'Контрольная сумма контентного слепка, попавшего в backup.';
COMMENT ON COLUMN system.backup_artifact.source_resume_asset_id IS
'Ссылка на исходный asset резюме, если backup был построен вокруг него.';
COMMENT ON COLUMN system.backup_artifact.backup_metadata_json IS
'Компактная сводка backup-файла без хранения его содержимого в БД.';
COMMENT ON COLUMN system.backup_artifact.created_by_actor IS
'Кто создал backup через админку или pipeline.';
COMMENT ON COLUMN system.backup_artifact.created_at IS
'Момент создания backup.';

CREATE INDEX IF NOT EXISTS ix_backup_artifact_created_at
  ON system.backup_artifact (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_backup_artifact_snapshot_kind_created_at
  ON system.backup_artifact (snapshot_kind, created_at DESC);

CREATE TABLE IF NOT EXISTS system.import_candidate (
  import_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  storage_disk text NOT NULL DEFAULT 'local',
  storage_path text NOT NULL,
  checksum_sha256 text NOT NULL,
  content_schema_version text NOT NULL,
  parse_status text NOT NULL,
  review_summary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by_actor text NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  expires_at timestamptz NULL,
  CONSTRAINT uq_import_candidate_storage_path UNIQUE (storage_path),
  CONSTRAINT uq_import_candidate_checksum_sha256 UNIQUE (checksum_sha256)
);

COMMENT ON TABLE system.import_candidate IS
'Metadata staged import-кандидатов, где сами payload лежат в файлах.';
COMMENT ON COLUMN system.import_candidate.import_candidate_id IS
'Идентификатор импорт-кандидата.';
COMMENT ON COLUMN system.import_candidate.storage_disk IS
'Тип хранилища импортируемого bundle-файла.';
COMMENT ON COLUMN system.import_candidate.storage_path IS
'Путь к импортируемому файлу на диске или в объектном хранилище.';
COMMENT ON COLUMN system.import_candidate.checksum_sha256 IS
'Контрольная сумма импортируемого файла.';
COMMENT ON COLUMN system.import_candidate.content_schema_version IS
'Версия импортируемого контентного формата.';
COMMENT ON COLUMN system.import_candidate.parse_status IS
'Статус разбора импортируемого файла: parsed, warning, failed.';
COMMENT ON COLUMN system.import_candidate.review_summary_json IS
'Краткая сводка кандидата для review в админке.';
COMMENT ON COLUMN system.import_candidate.created_by_actor IS
'Кто загрузил файл на review.';
COMMENT ON COLUMN system.import_candidate.created_at IS
'Время создания импорт-кандидата.';
COMMENT ON COLUMN system.import_candidate.expires_at IS
'Момент, после которого staged import можно автоматически удалить.';

CREATE INDEX IF NOT EXISTS ix_import_candidate_expires_at
  ON system.import_candidate (expires_at);

CREATE TABLE IF NOT EXISTS system.admin_content_state (
  state_key text PRIMARY KEY,
  source_metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_import_status text NOT NULL,
  last_imported_at timestamptz NULL,
  pending_import_candidate_id uuid NULL REFERENCES system.import_candidate (import_candidate_id) ON DELETE SET NULL,
  current_backup_artifact_id uuid NULL REFERENCES system.backup_artifact (backup_id) ON DELETE SET NULL,
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE system.admin_content_state IS
'Служебное состояние админки и импорта, не участвующее в SSR как основной источник.';
COMMENT ON COLUMN system.admin_content_state.state_key IS
'Ключ singleton-состояния, например content_admin.';
COMMENT ON COLUMN system.admin_content_state.source_metadata_json IS
'Вынесенное служебное состояние админки, импорта, warnings и manual overrides.';
COMMENT ON COLUMN system.admin_content_state.last_import_status IS
'Результат последнего импорта в админском контуре.';
COMMENT ON COLUMN system.admin_content_state.last_imported_at IS
'Время последнего завершенного импорта.';
COMMENT ON COLUMN system.admin_content_state.pending_import_candidate_id IS
'Импорт-кандидат, который еще находится в review.';
COMMENT ON COLUMN system.admin_content_state.current_backup_artifact_id IS
'Последний созданный backup bundle для быстрых сценариев rollback.';
COMMENT ON COLUMN system.admin_content_state.updated_at IS
'Время последнего обновления служебного состояния админки.';

CREATE TABLE IF NOT EXISTS system.runtime_health_snapshot (
  snapshot_key text PRIMARY KEY,
  health_json jsonb NOT NULL,
  source_kind text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE system.runtime_health_snapshot IS
'Компактный fallback-источник health-состояния для админки.';
COMMENT ON COLUMN system.runtime_health_snapshot.snapshot_key IS
'Ключ singleton-снимка, например current.';
COMMENT ON COLUMN system.runtime_health_snapshot.health_json IS
'Короткий актуальный статус сервисов и среды выполнения.';
COMMENT ON COLUMN system.runtime_health_snapshot.source_kind IS
'Источник health snapshot: internal-probe, prometheus-exporter или manual-check.';
COMMENT ON COLUMN system.runtime_health_snapshot.updated_at IS
'Время последнего обновления health snapshot.';

CREATE TABLE IF NOT EXISTS analytics.session_daily (
  event_day date NOT NULL,
  entry_route_key text NOT NULL,
  locale_code text NOT NULL,
  consent_state text NOT NULL DEFAULT 'accepted',
  storage_mode text NOT NULL,
  session_count bigint NOT NULL DEFAULT 0 CHECK (session_count >= 0),
  blocked_count bigint NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
  rollback_count bigint NOT NULL DEFAULT 0 CHECK (rollback_count >= 0),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_session_daily PRIMARY KEY (event_day, entry_route_key, locale_code, consent_state, storage_mode)
) PARTITION BY RANGE (event_day);

COMMENT ON TABLE analytics.session_daily IS
'Агрегированное число валидных обезличенных сессий за день. Таблица-предок monthly partitions.';
COMMENT ON COLUMN analytics.session_daily.event_day IS
'День, к которому относится агрегат.';
COMMENT ON COLUMN analytics.session_daily.entry_route_key IS
'Маршрут первого входа в сессию.';
COMMENT ON COLUMN analytics.session_daily.locale_code IS
'Локаль, по которой учитывается сессия.';
COMMENT ON COLUMN analytics.session_daily.consent_state IS
'Состояние согласия. В текущем контуре фактически хранится только accepted.';
COMMENT ON COLUMN analytics.session_daily.storage_mode IS
'Где клиент сохранил анонимный технический маркер согласия или сессии.';
COMMENT ON COLUMN analytics.session_daily.session_count IS
'Число валидных засчитанных сессий.';
COMMENT ON COLUMN analytics.session_daily.blocked_count IS
'Количество сессий, отброшенных антинакруточной логикой.';
COMMENT ON COLUMN analytics.session_daily.rollback_count IS
'Количество ранее учтенных сессий, откатанных после выявления аномалии.';
COMMENT ON COLUMN analytics.session_daily.updated_at IS
'Время последнего обновления агрегата.';

CREATE TABLE IF NOT EXISTS analytics.session_total (
  entry_route_key text NOT NULL,
  locale_code text NOT NULL,
  consent_state text NOT NULL DEFAULT 'accepted',
  storage_mode text NOT NULL,
  session_count_total bigint NOT NULL DEFAULT 0 CHECK (session_count_total >= 0),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_session_total PRIMARY KEY (entry_route_key, locale_code, consent_state, storage_mode)
);

COMMENT ON TABLE analytics.session_total IS
'Накопительная all-time статистика по сессиям для админских графиков.';
COMMENT ON COLUMN analytics.session_total.entry_route_key IS
'Маршрут первого входа в сессию.';
COMMENT ON COLUMN analytics.session_total.locale_code IS
'Локаль сессии.';
COMMENT ON COLUMN analytics.session_total.consent_state IS
'Состояние согласия. В текущей модели предполагается accepted.';
COMMENT ON COLUMN analytics.session_total.storage_mode IS
'Способ сохранения анонимного технического маркера.';
COMMENT ON COLUMN analytics.session_total.session_count_total IS
'All-time total по сессиям для админского dashboard.';
COMMENT ON COLUMN analytics.session_total.updated_at IS
'Время последнего обновления накопительного агрегата.';

CREATE TABLE IF NOT EXISTS analytics.section_view_daily (
  event_day date NOT NULL,
  route_key text NOT NULL,
  section_key text NOT NULL,
  locale_code text NOT NULL,
  view_source text NOT NULL,
  view_count bigint NOT NULL DEFAULT 0 CHECK (view_count >= 0),
  blocked_count bigint NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
  rollback_count bigint NOT NULL DEFAULT 0 CHECK (rollback_count >= 0),
  last_anomaly_at timestamptz NULL,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_section_view_daily PRIMARY KEY (event_day, route_key, section_key, locale_code, view_source)
) PARTITION BY RANGE (event_day);

COMMENT ON TABLE analytics.section_view_daily IS
'Агрегированные просмотры разделов сайта по дням. Таблица-предок monthly partitions.';
COMMENT ON COLUMN analytics.section_view_daily.event_day IS
'День агрегирования просмотров.';
COMMENT ON COLUMN analytics.section_view_daily.route_key IS
'Маршрут страницы, на которой показан раздел.';
COMMENT ON COLUMN analytics.section_view_daily.section_key IS
'Ключ секции внутри страницы, например hero или projects_grid.';
COMMENT ON COLUMN analytics.section_view_daily.locale_code IS
'Локаль, в которой был просмотрен раздел.';
COMMENT ON COLUMN analytics.section_view_daily.view_source IS
'Способ засчета просмотра: ssr_render, viewport_visible или rehydrated_visible.';
COMMENT ON COLUMN analytics.section_view_daily.view_count IS
'Число валидных просмотров секции.';
COMMENT ON COLUMN analytics.section_view_daily.blocked_count IS
'Подозрительные просмотры, не попавшие в итоговый счетчик.';
COMMENT ON COLUMN analytics.section_view_daily.rollback_count IS
'Просмотры, откатанные после аномального всплеска.';
COMMENT ON COLUMN analytics.section_view_daily.last_anomaly_at IS
'Последний момент срабатывания антинакруточной защиты.';
COMMENT ON COLUMN analytics.section_view_daily.updated_at IS
'Время обновления агрегата просмотров.';

CREATE TABLE IF NOT EXISTS analytics.section_view_total (
  route_key text NOT NULL,
  section_key text NOT NULL,
  locale_code text NOT NULL,
  view_source text NOT NULL,
  view_count_total bigint NOT NULL DEFAULT 0 CHECK (view_count_total >= 0),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_section_view_total PRIMARY KEY (route_key, section_key, locale_code, view_source)
);

COMMENT ON TABLE analytics.section_view_total IS
'Накопительные all-time просмотры секций для admin dashboard.';
COMMENT ON COLUMN analytics.section_view_total.route_key IS
'Маршрут страницы.';
COMMENT ON COLUMN analytics.section_view_total.section_key IS
'Ключ секции внутри страницы.';
COMMENT ON COLUMN analytics.section_view_total.locale_code IS
'Локаль просмотра.';
COMMENT ON COLUMN analytics.section_view_total.view_source IS
'Сценарий засчета просмотра.';
COMMENT ON COLUMN analytics.section_view_total.view_count_total IS
'Общий накопительный счетчик просмотров секции.';
COMMENT ON COLUMN analytics.section_view_total.updated_at IS
'Время последнего обновления all-time агрегата просмотров.';

CREATE TABLE IF NOT EXISTS analytics.section_click_daily (
  event_day date NOT NULL,
  route_key text NOT NULL,
  section_key text NOT NULL,
  action_key text NOT NULL,
  locale_code text NOT NULL,
  click_count bigint NOT NULL DEFAULT 0 CHECK (click_count >= 0),
  blocked_count bigint NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
  rollback_count bigint NOT NULL DEFAULT 0 CHECK (rollback_count >= 0),
  last_anomaly_at timestamptz NULL,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_section_click_daily PRIMARY KEY (event_day, route_key, section_key, action_key, locale_code)
) PARTITION BY RANGE (event_day);

COMMENT ON TABLE analytics.section_click_daily IS
'Агрегированные клики по действиям на сайте по дням. Таблица-предок monthly partitions.';
COMMENT ON COLUMN analytics.section_click_daily.event_day IS
'День агрегирования кликов.';
COMMENT ON COLUMN analytics.section_click_daily.route_key IS
'Маршрут страницы, на которой произошел клик.';
COMMENT ON COLUMN analytics.section_click_daily.section_key IS
'Ключ секции, внутри которой произошел клик.';
COMMENT ON COLUMN analytics.section_click_daily.action_key IS
'Ключ действия, например open_project, download_cv или switch_locale.';
COMMENT ON COLUMN analytics.section_click_daily.locale_code IS
'Локаль клика.';
COMMENT ON COLUMN analytics.section_click_daily.click_count IS
'Число валидных кликов.';
COMMENT ON COLUMN analytics.section_click_daily.blocked_count IS
'Подозрительные клики, отброшенные антинакруточной логикой.';
COMMENT ON COLUMN analytics.section_click_daily.rollback_count IS
'Клики, откатанные после аномального всплеска.';
COMMENT ON COLUMN analytics.section_click_daily.last_anomaly_at IS
'Последний момент срабатывания антиспам-защиты по кликам.';
COMMENT ON COLUMN analytics.section_click_daily.updated_at IS
'Время обновления агрегата кликов.';

CREATE TABLE IF NOT EXISTS analytics.section_click_total (
  route_key text NOT NULL,
  section_key text NOT NULL,
  action_key text NOT NULL,
  locale_code text NOT NULL,
  click_count_total bigint NOT NULL DEFAULT 0 CHECK (click_count_total >= 0),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_section_click_total PRIMARY KEY (route_key, section_key, action_key, locale_code)
);

COMMENT ON TABLE analytics.section_click_total IS
'Накопительные all-time клики по действиям для админских графиков.';
COMMENT ON COLUMN analytics.section_click_total.route_key IS
'Маршрут страницы.';
COMMENT ON COLUMN analytics.section_click_total.section_key IS
'Ключ секции внутри страницы.';
COMMENT ON COLUMN analytics.section_click_total.action_key IS
'Ключ пользовательского действия внутри секции.';
COMMENT ON COLUMN analytics.section_click_total.locale_code IS
'Локаль, в которой произошел клик.';
COMMENT ON COLUMN analytics.section_click_total.click_count_total IS
'Общий накопительный счетчик кликов.';
COMMENT ON COLUMN analytics.section_click_total.updated_at IS
'Время последнего обновления all-time агрегата кликов.';

CREATE TABLE IF NOT EXISTS audit.admin_action_log (
  log_id uuid NOT NULL DEFAULT gen_random_uuid(),
  occurred_at timestamptz NOT NULL,
  actor_subject text NULL,
  actor_login text NULL,
  action_code text NOT NULL,
  entity_type text NOT NULL,
  entity_key text NULL,
  change_summary_json jsonb NULL,
  request_id text NULL,
  result_code text NOT NULL,
  metadata_json jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_admin_action_log PRIMARY KEY (occurred_at, log_id)
) PARTITION BY RANGE (occurred_at);

COMMENT ON TABLE audit.admin_action_log IS
'Минимальный журнал действий админки с помесячным партиционированием.';
COMMENT ON COLUMN audit.admin_action_log.log_id IS
'Идентификатор audit-события.';
COMMENT ON COLUMN audit.admin_action_log.occurred_at IS
'Время события и ключ партиционирования.';
COMMENT ON COLUMN audit.admin_action_log.actor_subject IS
'Внешний subject из SSO или JWKS.';
COMMENT ON COLUMN audit.admin_action_log.actor_login IS
'Читаемый логин или email актера для расследований.';
COMMENT ON COLUMN audit.admin_action_log.action_code IS
'Код операции, например publish_snapshot, delete_backup или apply_import_candidate.';
COMMENT ON COLUMN audit.admin_action_log.entity_type IS
'Тип сущности, над которой было выполнено действие.';
COMMENT ON COLUMN audit.admin_action_log.entity_key IS
'Идентификатор сущности в удобном для UI виде.';
COMMENT ON COLUMN audit.admin_action_log.change_summary_json IS
'Краткий diff или summary изменения без хранения полного документа.';
COMMENT ON COLUMN audit.admin_action_log.request_id IS
'Связь с API-запросом для поиска в связанных системах наблюдаемости.';
COMMENT ON COLUMN audit.admin_action_log.result_code IS
'Итог операции: success, blocked, failed и подобные значения.';
COMMENT ON COLUMN audit.admin_action_log.metadata_json IS
'Редкие служебные детали события без разрастания основной схемы.';
COMMENT ON COLUMN audit.admin_action_log.created_at IS
'Техническое время записи строки аудита.';

CREATE INDEX IF NOT EXISTS ix_admin_action_log_action_code_occurred_at
  ON audit.admin_action_log (action_code, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_admin_action_log_entity_type_entity_key
  ON audit.admin_action_log (entity_type, entity_key);

COMMENT ON SCHEMA analytics IS
'Схема обезличенной агрегированной аналитики с помесячными партициями и retention-политиками.';
COMMENT ON SCHEMA audit IS
'Схема минимального журнала действий админки с временным партиционированием.';
COMMENT ON SCHEMA system IS
'Схема служебного состояния админки, health snapshot и реестров backup/import.';
