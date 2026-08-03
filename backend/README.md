# Backend

Backend реализуется на FastAPI с разделением на модули `api`, `application`, `domain`, `infrastructure` и `cache`.

## Что уже есть

- `create_app()` с CORS, health-check и модульными роутерами;
- базовая конфигурация через `BaseSettings`;
- общий формат ошибок API;
- первый вертикальный модуль `projects`;
- стартовые модули `profile` и `localization`;
- каркас настроек throttling для административного входа.

## Что требуется подключить дальше

1. Python 3.13 и `uv` для реального запуска.
2. Alembic-миграции и SQLAlchemy-модели.
3. Redis-кэш и PostgreSQL-репозитории вместо заглушек.
4. JWKS/SSO-интеграцию для админского контура.

