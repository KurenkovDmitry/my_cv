# Backend

Backend реализуется на FastAPI с разделением на модули `api`, `application`, `domain`, `infrastructure` и `cache`.

## Что уже есть

- `create_app()` с CORS, health-check и модульными роутерами;
- базовая конфигурация через `BaseSettings`;
- общий формат ошибок API;
- PostgreSQL snapshots `draft/published`, аудит и Redis read-path;
- защищённый административный контур с session cookie, CSRF и throttling;
- публикация с автоматическим pre-replace backup;
- staged import с полной и выборочной заменой разделов;
- управляемое хранилище PDF/JPEG/PNG/WebP для сертификатов, дипломов и изображений;
- переносимый `portfolio.bundle.v2`: snapshot и referenced assets в одном JSON-файле;
- проверка размера, magic bytes, checksum и path traversal для пользовательских файлов.

## Контент и файлы

Админка сохраняет всю редактируемую модель в одном `portfolio.v1` snapshot. Файлы не
попадают в PostgreSQL: snapshot содержит стабильные `*AssetId`, а content-service владеет
отдельным storage volume. Публичная выдача выполняется через
`GET /api/public/portfolio/assets/{asset_id}`.

Основные административные endpoints:

- `PUT /api/admin/content/draft` — сохранить полный draft;
- `POST /api/admin/content/publish` — опубликовать draft;
- `GET|POST|DELETE /api/admin/content/assets` — реестр и загрузка файлов;
- `POST /api/admin/system/backups` — создать полный backup;
- `POST /api/admin/system/import-candidates` — загрузить bundle на review;
- `POST /api/admin/system/import-candidates/{id}/apply-to-draft` — восстановить данные и файлы.

Для persistent storage обязательны volume и переменные:

```env
BACKUP_STORAGE_PATH=/opt/portfolio/backups
CONTENT_ASSET_STORAGE_PATH=/opt/portfolio/assets
CONTENT_ASSET_MAX_BYTES=20971520
```

Исходная фотография, пять сертификатов и диплом Технопарка загружаются в пустой volume
идемпотентно при старте приложения. Повторный старт не перезаписывает пользовательские файлы.

## Что требуется подключить дальше

1. Python 3.13 и `uv` для реального запуска.
2. JWKS/SSO-интеграцию с целевым user-service вместо локальной bootstrap-сессии.
3. S3-compatible adapter вместо local volume, если сайт будет развёрнут в нескольких API-репликах.
