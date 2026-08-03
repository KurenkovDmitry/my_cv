# Черновик схемы БД

Документ подготовлен **до создания БД** и уже переработан под текущие решения:

- запись редкая, чтение частое;
- SSR должен по возможности читать готовый слепок сразу;
- сильная нормализация не нужна;
- где контент читается целиком, используем `jsonb`;
- в БД храним только **актуальное состояние**;
- старые версии контента храним **в экспортных файлах**, а не в БД;
- логи в БД минимизируем;
- аналитику храним **обезличенно и агрегированно**;
- таблицы логов и аналитики делим по времени;
- к каждой таблице и каждому полю в будущем добавляется SQL-комментарий.

---

## 1. Основной принцип

Для этого проекта PostgreSQL не должен быть архивом всех состояний системы.

Он должен хранить:

- текущий опубликованный слепок сайта;
- текущий черновик для админки;
- метаданные медиа;
- служебное состояние импорта и контентного контура админки;
- метаданные backup/export артефактов;
- staged import candidate для контроля замены;
- компактный health snapshot;
- обезличенную агрегированную аналитику;
- минимальный admin audit.

Он **не должен** хранить:

- все исторические версии контента;
- полный журнал кликов;
- сырые логи приложения;
- старые экспортные payload целиком;
- тяжёлые отчёты мониторинга;
- полные Grafana/Prometheus time series;
- raw diff между версиями.

---

## 2. Почему здесь `jsonb`, а не десятки подтаблиц

Ваш контент:

- меняется редко;
- читается часто;
- приходит в SSR почти готовым;
- не требует сложных join на каждый пользовательский запрос;
- по происхождению ближе к документу резюме, чем к тяжёлой ERP-модели.

Поэтому логичнее хранить **готовый контентный слепок** в `jsonb`, чем дробить всё на:

- `profile_i18n`;
- `project_i18n`;
- `skill_i18n`;
- `education_i18n`;
- `experience_i18n`;
- `theme_i18n`;
- дополнительные link-таблицы почти для каждого раздела.

Это особенно полезно для:

- SSR;
- preview в админке;
- импорт/экспорт сценариев;
- rollback через backup bundle;
- быстрого cold-start восстановления Redis/cache.

---

## 3. Где `jsonb` здесь применяется

### 3.1. Для основного слепка сайта

В таблице `public.portfolio_snapshot.content_json`.

Туда попадает:

- профиль;
- проекты;
- опыт;
- образование;
- навыки;
- темы;
- локализация;
- accessibility;
- SEO;
- текст модалки согласия;
- другие редактируемые блоки.

### 3.2. Для служебного состояния админки

В таблице `system.admin_content_state.source_metadata_json`.

Туда попадает:

- warnings после импорта;
- manual overrides;
- информация о последнем источнике;
- технические статусы админского контура.

### 3.3. Для метаданных медиа

В таблице `public.media_asset.image_metadata_json`.

Туда попадает:

- размер изображения;
- dominant color;
- дополнительные свойства файла.

### 3.4. Для backup/import метаданных

В таблицах `system.backup_artifact.backup_metadata_json` и `system.import_candidate.review_summary_json`.

Туда попадает:

- краткая сводка содержимого;
- предупреждения;
- технические флаги готовности к применению.

### 3.5. Для runtime health snapshot

В таблице `system.runtime_health_snapshot.health_json`.

Туда попадает:

- текущий статус сервисов;
- свободный диск;
- краткие показатели среды.

---

## 4. Пример `jsonb` в основном слепке

Пример поля `content_json`:

```json
{
  "profile": {
    "displayName": {
      "ru": "Д. А. Куренков",
      "en": "D. A. Kurenkov"
    },
    "headline": {
      "ru": "Инженер, который соединяет highload-мышление, инфраструктуру и аккуратный интерфейс.",
      "en": "An engineer connecting highload thinking, infrastructure, and refined interface design."
    },
    "summary": {
      "ru": "Краткое описание профиля.",
      "en": "Short profile summary."
    },
    "avatarAssetId": "f5f6d0b1-0a4a-4c33-a5d9-a62f6f4e31a4"
  },
  "projects": [
    {
      "slug": "portfolio-platform",
      "featured": true,
      "title": {
        "ru": "Платформа персонального портфолио",
        "en": "Personal portfolio platform"
      },
      "summary": {
        "ru": "Краткое описание проекта.",
        "en": "Short project summary."
      },
      "technologies": ["TypeScript", "React", "FastAPI"],
      "links": [
        {
          "kind": "repository",
          "label": {
            "ru": "Исходный код",
            "en": "Source code"
          },
          "href": "#"
        }
      ]
    }
  ],
  "experience": [],
  "education": [],
  "skills": [],
  "themes": {
    "active": "paper-sand",
    "available": [
      {
        "id": "paper-sand",
        "label": {
          "ru": "Тёплый песок",
          "en": "Paper sand"
        }
      }
    ]
  },
  "localization": {
    "defaultLocale": "en",
    "supportedLocales": ["en", "ru"],
    "autoDetectByRegion": {
      "RU": "ru"
    }
  },
  "accessibility": {
    "speechSynthesisEnabled": true,
    "highContrastModeEnabled": true,
    "reducedMotionPresetEnabled": true
  },
  "legal": {
    "analyticsConsent": {
      "version": "2026-08-03",
      "modalTitle": {
        "ru": "Согласие на обезличенную аналитику",
        "en": "Consent for anonymous analytics"
      },
      "modalBodyMarkdown": {
        "ru": "Сайт собирает только обезличенную агрегированную статистику просмотров и кликов.",
        "en": "The site collects only anonymous aggregated statistics about views and clicks."
      }
    }
  }
}
```

---

## 5. Основные таблицы

## 5.1. `public.portfolio_snapshot`

### Назначение таблицы

Главная таблица публичного и редакторского контента.

Она хранит:

- текущий `published` слепок;
- текущий `draft` слепок.

Базовая цель:

```text
один SSR-запрос → одна таблица → одна строка
```

### Поля

- `id uuid pk`
  зачем нужен:
  технический первичный ключ записи слепка.

- `snapshot_kind text not null unique`
  зачем нужен:
  позволяет хранить режимы вроде `published` и `draft` и выбирать нужный слепок без join.

- `content_schema_version text not null`
  зачем нужен:
  фиксирует версию формата `content_json`, чтобы backend и админка знали, как его валидировать.

- `content_json jsonb not null`
  зачем нужен:
  содержит весь текущий контент сайта в одной записи для SSR, preview, импорта и экспорта.

- `content_checksum_sha256 text not null`
  зачем нужен:
  используется для ETag, контроля целостности и инвалидирования кэшей.

- `published_locale_codes jsonb not null`
  зачем нужен:
  позволяет быстро получить список реально опубликованных локалей без разбора всего документа.

  пример:

  ```json
  ["en", "ru"]
  ```

- `is_active boolean not null default false`
  зачем нужен:
  явный флаг активного слепка для безопасной логики переключения.

- `published_at timestamptz null`
  зачем нужен:
  хранит момент публикации текущего слепка.

- `created_at timestamptz not null default NOW()`
  зачем нужен:
  время создания строки слепка.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время последнего изменения слепка.

### Что намеренно вынесено отсюда

`source_metadata_json` здесь **не хранится**, потому что это служебная информация админки, а не публичного runtime-контура.

Она вынесена отдельно в `system.admin_content_state`.

### Индексы

- `unique(snapshot_kind)`
- `index(is_active, snapshot_kind)`

---

## 5.2. `public.media_asset`

### Назначение таблицы

Единый реестр файлов и медиа:

- аватар;
- изображения проектов;
- резюме;
- og:image;
- будущие загружаемые ассеты.

### Поля

- `id uuid pk`
  зачем нужен:
  стабильный идентификатор ассета.

- `asset_kind text not null`
  зачем нужен:
  позволяет различать `avatar`, `project_cover`, `resume_source`, `open_graph_image` и другие типы.

- `storage_disk text not null default 'local'`
  зачем нужен:
  указывает тип хранилища, например `local`, `s3`, `object-storage`.

- `storage_path text not null`
  зачем нужен:
  путь к файлу в хранилище.

- `public_url text null`
  зачем нужен:
  готовая ссылка для отдачи, если asset уже экспонируется напрямую.

- `mime_type text not null`
  зачем нужен:
  нужен для безопасной отдачи и валидации типа файла.

- `original_filename text null`
  зачем нужен:
  помогает в админке и при диагностике видеть исходное имя файла.

- `file_size_bytes bigint not null`
  зачем нужен:
  контроль веса файла и лимитов сервера.

- `checksum_sha256 text not null`
  зачем нужен:
  дедупликация и контроль целостности.

- `image_metadata_json jsonb null`
  зачем нужен:
  хранит необязательные свойства изображения в одном поле.

  пример:

  ```json
  {
    "widthPx": 1280,
    "heightPx": 720,
    "dominantColor": "#d8c6b5"
  }
  ```

- `alt_json jsonb null`
  зачем нужен:
  локализованные `alt`-тексты без отдельной подтаблицы.

  пример:

  ```json
  {
    "ru": "Портрет владельца сайта",
    "en": "Portrait of the site owner"
  }
  ```

- `created_at timestamptz not null default NOW()`
  зачем нужен:
  время регистрации ассета.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время последнего обновления метаданных ассета.

### Индексы

- `unique(storage_path)`
- `unique(checksum_sha256)`
- `index(asset_kind)`

---

## 5.3. `system.admin_content_state`

### Назначение таблицы

Хранит служебное состояние именно для админского контентного контура.

Эта таблица не используется как основной источник для SSR.

### Поля

- `state_key text pk`
  зачем нужен:
  позволяет хранить singleton-state, например `content_admin`.

- `source_metadata_json jsonb not null default '{}'::jsonb`
  зачем нужен:
  вынесенное служебное состояние админки и импорта.

  пример:

  ```json
  {
    "lastSourceType": "resume_pdf",
    "lastSourceFilename": "resume-2026-07-22.pdf",
    "warnings": [
      "Не удалось однозначно определить даты по одному месту работы."
    ],
    "manualOverrides": [
      "profile.summary.ru",
      "projects[0].summary.en"
    ]
  }
  ```

- `last_import_status text not null`
  зачем нужен:
  показывает результат последнего импорта.

- `last_imported_at timestamptz null`
  зачем нужен:
  время последнего импорта.

- `pending_import_candidate_id uuid null`
  зачем нужен:
  ссылка на импорт-кандидат, который ещё проходит review.

- `current_backup_artifact_id uuid null`
  зачем нужен:
  быстрый указатель на последний созданный backup bundle.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время последнего обновления админского служебного состояния.

---

## 5.4. `system.backup_artifact`

### Назначение таблицы

Реестр backup/export файлов, которые можно:

- скачать из админки;
- сравнить с текущей версией;
- сравнить между собой;
- импортировать обратно;
- удалить физически.

Удаление здесь должно быть **настоящим удалением**, без `is_deleted`.

### Поля

- `backup_id uuid pk`
  зачем нужен:
  первичный ключ backup-артефакта.

- `backup_kind text not null default 'export_bundle'`
  зачем нужен:
  тип артефакта, например `export_bundle`, `pre_replace_backup`, `manual_backup`.

- `storage_disk text not null default 'local'`
  зачем нужен:
  хранилище backup-файла.

- `storage_path text not null`
  зачем нужен:
  путь к backup-файлу, который можно скачать и импортировать обратно.

- `file_size_bytes bigint not null`
  зачем нужен:
  контроль размера артефакта.

- `checksum_sha256 text not null`
  зачем нужен:
  проверка целостности и дедупликация.

- `content_schema_version text not null`
  зачем нужен:
  фиксирует версию формата backup bundle.

- `snapshot_kind text not null`
  зачем нужен:
  показывает, из какого состояния был сделан backup: `draft`, `published`, `before_replace`.

- `snapshot_checksum_sha256 text not null`
  зачем нужен:
  контроль, какой именно контентный слепок попал в backup.

- `source_resume_asset_id uuid null`
  зачем нужен:
  если backup связан с резюме или конкретным исходным документом.

- `backup_metadata_json jsonb not null default '{}'::jsonb`
  зачем нужен:
  компактная сводка backup-файла без хранения его содержимого в БД.

  пример:

  ```json
  {
    "locales": ["ru", "en"],
    "projectsCount": 6,
    "hasManualOverrides": true
  }
  ```

- `created_by_actor text null`
  зачем нужен:
  кто создал backup через админку или pipeline.

- `created_at timestamptz not null default NOW()`
  зачем нужен:
  момент создания backup.

### Индексы

- `unique(storage_path)`
- `unique(checksum_sha256)`
- `index(created_at desc)`
- `index(snapshot_kind, created_at desc)`

---

## 5.5. `system.import_candidate`

### Назначение таблицы

Хранит metadata для staged import, который работает как контроль версий:

- загружаем файл;
- парсим;
- сравниваем с текущим состоянием;
- подтверждаем, что заменяем;
- можно заменить всё целиком;
- можно применить выборочно по блокам.

Сам импортируемый payload лежит в файле, а не в БД.

### Поля

- `import_candidate_id uuid pk`
  зачем нужен:
  идентификатор импорт-кандидата.

- `storage_disk text not null default 'local'`
  зачем нужен:
  хранилище файла импорта.

- `storage_path text not null`
  зачем нужен:
  путь к импортируемому bundle-файлу.

- `checksum_sha256 text not null`
  зачем нужен:
  контроль целостности импортируемого файла.

- `content_schema_version text not null`
  зачем нужен:
  версия импортируемого формата.

- `parse_status text not null`
  зачем нужен:
  показывает, удалось ли распарсить файл и готов ли он к review.

- `review_summary_json jsonb not null default '{}'::jsonb`
  зачем нужен:
  краткая сводка кандидата для админки.

  пример:

  ```json
  {
    "replaceableSections": [
      "profile",
      "projects",
      "experience"
    ],
    "warningsCount": 1,
    "canReplaceFully": true
  }
  ```

- `created_by_actor text null`
  зачем нужен:
  кто загрузил файл на review.

- `created_at timestamptz not null default NOW()`
  зачем нужен:
  время создания импорт-кандидата.

- `expires_at timestamptz null`
  зачем нужен:
  позволяет чистить просроченные staged import без накопления мусора.

### Что не хранить тут

Не нужно хранить:

- полный diff;
- полный импортируемый payload;
- историю каждого шага сравнения.

Это либо лежит в файле, либо генерируется on-demand.

---

## 5.6. `system.runtime_health_snapshot`

### Назначение таблицы

Компактный fallback-источник для админки, если полноценная Grafana не поднята или сервер её не тянет.

### Поля

- `snapshot_key text pk`
  зачем нужен:
  singleton-ключ, например `current`.

- `health_json jsonb not null`
  зачем нужен:
  хранит короткий актуальный статус контуров.

  пример:

  ```json
  {
    "api": "ok",
    "postgres": "ok",
    "redis": "ok",
    "diskFreeMb": 6120,
    "memoryPressure": "low"
  }
  ```

- `source_kind text not null`
  зачем нужен:
  источник health snapshot: `internal-probe`, `prometheus-exporter`, `manual-check`.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  свежесть записи.

### Про Grafana

Grafana разрешена только если сервер реально вытягивает её по ресурсам.

Если не вытягивает:

- admin читает `system.runtime_health_snapshot`;
- long-term timeseries не храним.

Если вытягивает:

- admin показывает графики и логи из Grafana/Prometheus;
- таблица `system.runtime_health_snapshot` остаётся fallback-слоем.

---

## 6. Обезличенная аналитика

## 6.1. Общие правила аналитики

Аналитика должна быть:

- без IP;
- без user id;
- без fingerprint;
- без постоянного browser id;
- без хранения сырого event log в PostgreSQL;
- только в виде агрегатов.

### Как хранить техническое согласие

Приоритет хранения:

1. `localStorage`
2. `IndexedDB`
3. `sessionStorage`
4. server-set cookie

### Важное уточнение по cookie и `HttpOnly`

Так как вы хотите приоритет `localStorage`, а cookie только как дополнительный серверный маркер, схема такая:

- основной client-side флаг согласия хранится в `localStorage`;
- после подтверждения frontend вызывает endpoint;
- backend при необходимости выставляет **дополнительную** cookie:
  `HttpOnly`, `Secure`, `SameSite=Lax`;
- эта cookie нужна не для идентификации пользователя, а для SSR/edge-side понимания, что consent уже был принят.

То есть:

- `localStorage` приоритетнее;
- cookie возможна как серверный дублирующий маркер;
- если используется cookie, она должна быть `HttpOnly`.

### Что делать при отказе

Пользователь не должен продолжать пользоваться сайтом без согласия на такую аналитику.

Если пользователь нажимает отказ:

- сайт закрывается для дальнейшей работы;
- аналитика не пишется;
- строка `rejected` в daily analytics не создаётся.

Поэтому в агрегатах production-режима основное значение:

- `accepted`

---

## 6.2. `analytics.session_daily`

### Назначение таблицы

Агрегированное количество валидных анонимных сессий за день.

### Поля

- `event_day date not null`
  зачем нужен:
  день, к которому относится агрегат.

- `entry_route_key text not null`
  зачем нужен:
  маршрут первого входа в сессию.

- `locale_code text not null`
  зачем нужен:
  аналитика по локалям.

- `consent_state text not null default 'accepted'`
  зачем нужен:
  фиксирует, что сессия учтена только после принятого согласия.

- `storage_mode text not null`
  зачем нужен:
  показывает, где был сохранён анонимный технический маркер согласия/сессии.

  рекомендуемые значения:
  `local_storage`, `indexed_db`, `session_storage`, `http_only_cookie`, `memory_only`

- `session_count bigint not null default 0`
  зачем нужен:
  число валидных засчитанных сессий.

- `blocked_count bigint not null default 0`
  зачем нужен:
  количество сессий, отброшенных антинакруточной логикой.

- `rollback_count bigint not null default 0`
  зачем нужен:
  количество ранее засчитанных сессий, откатанных после выявления аномалии.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время последнего обновления агрегата.

### Ключ

```text
pk(event_day, entry_route_key, locale_code, consent_state, storage_mode)
```

### Партиционирование

Эта таблица должна быть:

```text
PARTITION BY RANGE (event_day)
```

Режим:

- партиции по месяцам;
- автоматическое создание новых партиций заранее;
- retention по умолчанию: `1.5 года`;
- retention должен настраиваться через `.env`.

Рекомендуемый env:

```env
ANALYTICS_SESSION_DAILY_RETENTION_DAYS=548
```

---

## 6.3. `analytics.session_total`

### Назначение таблицы

Хранит общую накопительную статистику по сессиям, чтобы после удаления старых дневных партиций не терялась общая историчность.

### Поля

- `entry_route_key text not null`
  зачем нужен:
  маршрут первого входа.

- `locale_code text not null`
  зачем нужен:
  разрез по локали.

- `consent_state text not null default 'accepted'`
  зачем нужен:
  техническое подтверждение модели учёта.

- `storage_mode text not null`
  зачем нужен:
  как был сохранён технический маркер.

- `session_count_total bigint not null default 0`
  зачем нужен:
  all-time total по сессиям для admin dashboard.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  момент последнего обновления накопительного агрегата.

### Ключ

```text
pk(entry_route_key, locale_code, consent_state, storage_mode)
```

---

## 6.4. `analytics.section_view_daily`

### Назначение таблицы

Агрегированные просмотры разделов сайта по дням.

### Поля

- `event_day date not null`
  зачем нужен:
  день агрегирования.

- `route_key text not null`
  зачем нужен:
  маршрут страницы.

- `section_key text not null`
  зачем нужен:
  идентификатор блока, например `hero`, `projects_grid`, `experience_timeline`.

- `locale_code text not null`
  зачем нужен:
  аналитика по локали.

- `view_source text not null`
  зачем нужен:
  способ засчёта просмотра.

  рекомендуемые значения:
  `ssr_render`, `viewport_visible`, `rehydrated_visible`

- `view_count bigint not null default 0`
  зачем нужен:
  число валидных просмотров.

- `blocked_count bigint not null default 0`
  зачем нужен:
  число подозрительных просмотров, отброшенных антиспамом.

- `rollback_count bigint not null default 0`
  зачем нужен:
  число просмотров, откатанных после аномального всплеска.

- `last_anomaly_at timestamptz null`
  зачем нужен:
  последний момент срабатывания антинакруточной защиты.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время обновления агрегата.

### Ключ

```text
pk(event_day, route_key, section_key, locale_code, view_source)
```

### Партиционирование и retention

- monthly range partitions по `event_day`
- retention по умолчанию `365 дней`
- значение retention настраивается через `.env`

```env
ANALYTICS_SECTION_VIEW_DAILY_RETENTION_DAYS=365
```

---

## 6.5. `analytics.section_view_total`

### Назначение таблицы

All-time total по просмотрам секций, чтобы не терять общую статистику после чистки дневных партиций.

### Поля

- `route_key text not null`
  зачем нужен:
  маршрут страницы.

- `section_key text not null`
  зачем нужен:
  блок внутри страницы.

- `locale_code text not null`
  зачем нужен:
  локаль.

- `view_source text not null`
  зачем нужен:
  сценарий учёта.

- `view_count_total bigint not null default 0`
  зачем нужен:
  all-time total просмотров секции.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время обновления общего агрегата.

### Ключ

```text
pk(route_key, section_key, locale_code, view_source)
```

---

## 6.6. `analytics.section_click_daily`

### Назначение таблицы

Агрегированные клики по интерактивным действиям за день.

### Поля

- `event_day date not null`
  зачем нужен:
  день агрегирования.

- `route_key text not null`
  зачем нужен:
  маршрут страницы.

- `section_key text not null`
  зачем нужен:
  блок, внутри которого был клик.

- `action_key text not null`
  зачем нужен:
  конкретное действие, например `open_project`, `download_cv`, `switch_locale`.

- `locale_code text not null`
  зачем нужен:
  аналитика по локали.

- `click_count bigint not null default 0`
  зачем нужен:
  число валидных кликов.

- `blocked_count bigint not null default 0`
  зачем нужен:
  число отброшенных подозрительных кликов.

- `rollback_count bigint not null default 0`
  зачем нужен:
  число кликов, откатанных после аномалии.

- `last_anomaly_at timestamptz null`
  зачем нужен:
  последний момент антиспам-срабатывания.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время обновления агрегата.

### Ключ

```text
pk(event_day, route_key, section_key, action_key, locale_code)
```

### Партиционирование и retention

- monthly range partitions по `event_day`
- retention по умолчанию `365 дней`
- значение retention настраивается через `.env`

```env
ANALYTICS_SECTION_CLICK_DAILY_RETENTION_DAYS=365
```

---

## 6.7. `analytics.section_click_total`

### Назначение таблицы

All-time total по кликам для admin dashboard после чистки дневных партиций.

### Поля

- `route_key text not null`
  зачем нужен:
  маршрут страницы.

- `section_key text not null`
  зачем нужен:
  блок страницы.

- `action_key text not null`
  зачем нужен:
  действие внутри блока.

- `locale_code text not null`
  зачем нужен:
  локаль.

- `click_count_total bigint not null default 0`
  зачем нужен:
  общий накопительный счётчик кликов.

- `updated_at timestamptz not null default NOW()`
  зачем нужен:
  время обновления общего агрегата.

### Ключ

```text
pk(route_key, section_key, action_key, locale_code)
```

---

## 6.8. Как защищаться от `Ctrl+Shift+R` и накрутки

Сырые события в PostgreSQL хранить не надо.

Правильный контур:

1. Клиент создаёт короткоживущий **анонимный session nonce**.
2. Он хранится в:
   - `localStorage` как основной вариант;
   - fallback — в `IndexedDB`, `sessionStorage` или memory-only;
   - опционально backend зеркалит consent в `HttpOnly` cookie.
3. Перед записью агрегата backend проверяет nonce и event key в Redis с TTL.
4. Повторные одинаковые события за короткое окно не засчитываются.
5. Если есть резкий всплеск по комбинации:
   - `route_key`;
   - `section_key`;
   - `action_key`;
   backend:
   - не учитывает событие;
   - увеличивает `blocked_count`;
   - при необходимости делает откат и увеличивает `rollback_count`.

### Почему это соответствует обезличиванию

- нет IP;
- нет fingerprint;
- нет user id;
- нет постоянного browser id;
- нет сырых персонализированных логов.

---

## 7. Логи и аудит

## 7.1. `audit.admin_action_log`

### Назначение таблицы

Минимальный журнал действий админки:

- публикация;
- правка draft;
- импорт;
- замена контента;
- удаление backup;
- запуск сравнения версий;
- rollback/restore.

### Поля

- `log_id uuid not null`
  зачем нужен:
  идентификатор audit-события.

- `occurred_at timestamptz not null`
  зачем нужен:
  время события и ключ партиционирования.

- `actor_subject text null`
  зачем нужен:
  внешний subject из SSO/JWKS.

- `actor_login text null`
  зачем нужен:
  читаемое значение для админки и расследований.

- `action_code text not null`
  зачем нужен:
  код операции, например `publish_snapshot`, `delete_backup`, `apply_import_candidate`.

- `entity_type text not null`
  зачем нужен:
  тип сущности.

- `entity_key text null`
  зачем нужен:
  идентификатор сущности в удобном для UI виде.

- `change_summary_json jsonb null`
  зачем нужен:
  хранит **краткий diff**, а не полный before/after документ.

- `request_id text null`
  зачем нужен:
  связь с API-запросом.

- `result_code text not null`
  зачем нужен:
  итог операции.

- `metadata_json jsonb null`
  зачем нужен:
  редкие служебные детали события.

- `created_at timestamptz not null default NOW()`
  зачем нужен:
  техническое время записи строки.

### Партиционирование

Обязательно:

```text
PARTITION BY RANGE (occurred_at)
```

Режим:

- партиции по месяцам;
- создание заранее;
- автоудаление по retention.

### Retention

По умолчанию:

```env
AUDIT_LOG_RETENTION_DAYS=90
```

### Что не надо хранить в БД

Не хранить в PostgreSQL:

- access log nginx;
- каждый frontend hit;
- raw backend logs;
- трассировку каждого запроса.

Это должно жить:

- либо в файлах с rotation;
- либо в Loki/Grafana, если сервер реально вытягивает.

---

## 8. Backup, import и сравнение версий

## 8.1. Backup-модель

При замене контента:

- сначала создаётся backup bundle;
- backup bundle регистрируется в `system.backup_artifact`;
- затем только применяется новая версия.

Старые версии:

- не лежат в БД как контент;
- лежат как файлы importable/exportable формата;
- доступны для скачивания и удаления через админку.

## 8.2. Импорт как control version workflow

Админка должна поддерживать сценарий:

1. Загрузить backup/import bundle.
2. Создать `system.import_candidate`.
3. Сравнить candidate с:
   - текущим `draft`;
   - текущим `published`;
   - любым backup из `system.backup_artifact`.
4. Показать разницу по разделам:
   - `profile`;
   - `projects`;
   - `experience`;
   - `education`;
   - `skills`;
   - `themes`;
   - `legal`;
   - `seo`.
5. Дать выбрать:
   - что заменить;
   - что не заменять;
   - применить всё целиком.

В интерфейсе должны быть действия:

- `Подтверждаю, что хочу заменить выбранные разделы`
- `Полностью заменить текущую версию`

## 8.3. Сравнение backup vs current и backup vs backup

Это не должно храниться как историческая таблица diff в БД.

Нужен механизм:

- по запросу выбрать два файла;
- сравнить их;
- отдать diff в админку;
- при необходимости сохранить только временный artifact вне БД.

---

## 9. Native diff engine как Python-библиотека

Для сравнения backup-файлов и текущей версии нужно заложить отдельный модуль:

```text
tools/content-diff-native/
```

или

```text
libs/content_diff_native/
```

### Формат

Это должна быть **Python-библиотека с native core**:

- Python API для backend;
- C++ core для diff и нормализации;
- ассемблер/SIMD только в изолированном hot path и только после профилирования.

### Почему не хранить diff в БД

Потому что:

- сравнение — это on-demand операция;
- сервер небольшой;
- diff нужен для UI, а не как основной источник истины;
- файлы уже лежат отдельно как backup artifacts.

### Что должна уметь библиотека

- сравнивать:
  - current snapshot vs backup file;
  - backup file vs backup file;
  - import candidate vs draft/published;
- возвращать:
  - JSON diff summary;
  - список изменённых путей;
  - grouped diff по разделам;
  - human-readable diff для админки.

### Требование по производительности

Ассемблер использовать только если одновременно выполнены условия:

- есть подтверждённый bottleneck;
- есть benchmark до/после;
- C++ без ассемблера уже недостаточен;
- код изолирован в библиотеке;
- есть безопасный fallback.

То есть здесь сохраняется правило проекта:

```text
сначала C++ и профилирование,
потом при необходимости SIMD/assembler,
но не наоборот
```

### Интеграция

Рекомендуемый формат:

- Python extension через `pybind11` или аналогичную бесплатную библиотеку;
- backend вызывает её как обычный Python-модуль;
- diff не пишется в БД как постоянная сущность.

---

## 10. Графики в админке

В админке должны быть графики на основе:

- `analytics.session_daily`
- `analytics.section_view_daily`
- `analytics.section_click_daily`
- `analytics.session_total`
- `analytics.section_view_total`
- `analytics.section_click_total`

### Примеры графиков

- сессии по дням;
- просмотры ключевых секций по дням;
- клики по действиям по дням;
- топ разделов по просмотрам;
- топ CTA по кликам;
- all-time totals после очистки старых дневных партиций.

Если сервер тянет Grafana:

- admin может встраивать или проксировать графики оттуда.

Если не тянет:

- строим графики напрямую на собственных daily + total таблицах.

---

## 11. Комментарии к таблицам и полям в самой БД

Это обязательное требование для будущих миграций.

Для каждой таблицы:

```sql
COMMENT ON TABLE public.portfolio_snapshot IS
'Актуальный контентный слепок сайта. Используется для SSR, preview и экспорта.';
```

Для каждой колонки:

```sql
COMMENT ON COLUMN public.portfolio_snapshot.content_json IS
'Полный актуальный контент сайта в jsonb. Хранится целиком ради частого чтения без join.';
```

Это нужно сделать для:

- всех таблиц;
- всех колонок;
- всех partitioned parent tables;
- jsonb-полей с нетривиальным смыслом.

Чтобы комментарии отображались:

- в pgAdmin;
- в IDE;
- в introspection tools;
- в документации схемы.

---

## 12. Что включить в первую миграцию

### V1

- `public.portfolio_snapshot`
- `public.media_asset`
- `system.admin_content_state`
- `system.backup_artifact`
- `system.import_candidate`
- `system.runtime_health_snapshot`
- `analytics.session_daily`
- `analytics.session_total`
- `analytics.section_view_daily`
- `analytics.section_view_total`
- `analytics.section_click_daily`
- `analytics.section_click_total`
- `audit.admin_action_log`

### Что сознательно не включать отдельно в V1

Не выносить в отдельные таблицы:

- `profile_i18n`
- `project_i18n`
- `experience_i18n`
- `education_i18n`
- `skills_i18n`
- `themes_i18n`
- `route_seo`
- `content_version`
- `admin_user`
- `admin_session`

Потому что на текущем этапе:

- это перегрузит схему;
- усложнит SSR;
- усложнит импорт/экспорт;
- не даст реальной пользы при редкой записи.

---

## 13. Настройки `.env`, которые уже надо предусмотреть

```env
ANALYTICS_SESSION_DAILY_RETENTION_DAYS=548
ANALYTICS_SECTION_VIEW_DAILY_RETENTION_DAYS=365
ANALYTICS_SECTION_CLICK_DAILY_RETENTION_DAYS=365
AUDIT_LOG_RETENTION_DAYS=90
BACKUP_STORAGE_PATH=/opt/portfolio/backups
IMPORT_CANDIDATE_RETENTION_DAYS=30
ENABLE_GRAFANA_INTEGRATION=false
```

---

## 14. Что предлагаю сделать следующим шагом

После вашей правки этого документа:

1. зафиксирую окончательную схему;
2. добавлю SQLAlchemy-модели только для утверждённых таблиц;
3. подготовлю первую миграцию;
4. в миграции сразу проставлю `COMMENT ON TABLE` и `COMMENT ON COLUMN`;
5. заложу parent tables для monthly partitions;
6. подготовлю сервисный контур для backup/import/diff без хранения старых версий контента в БД.
