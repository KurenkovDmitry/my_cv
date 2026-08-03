# Deployment Notes

## Базовый контур

- `apps/web` и `apps/admin` собираются в статические bundles;
- `backend/` поднимается как отдельный FastAPI-сервис;
- `postgres` остаётся источником истины;
- `redis` используется только как кэш;
- `nginx` принимает внешний трафик и проксирует `/api/`.

## Ограничения

- целевой сервер ограничен примерно 4 ГБ RAM;
- тяжёлые проверки зависимостей и лицензий должны выполняться в CI, а не на production-сервере;
- `rules/` не должен попадать в build-артефакты и Docker-образы.

## Роли БД

- `POSTGRES_SUPERUSER_NAME` и `POSTGRES_SUPERUSER_PASSWORD` используются только для bootstrap PostgreSQL и первичного создания app-ролей;
- `DB_APP_READ_USERNAME` и `DB_APP_READ_PASSWORD` используются только для read-path запросов;
- `DB_APP_WRITE_USERNAME` и `DB_APP_WRITE_PASSWORD` используются для обычных mutation-path операций;
- `DB_APP_ADMIN_USERNAME` и `DB_APP_ADMIN_PASSWORD` используются для миграций, grant-sync, создания партиций и других сервисных операций с полными правами на app-базу;
- все имена и пароли хранятся в `.env`, а compose прокидывает bootstrap-секреты только в `postgres`, не в `api`.

## После миграций

- после применения схемы нужно запускать `scripts/postgres/refresh-app-grants.sh`;
- этот шаг обязателен после новых таблиц, новых партиций и изменений default privileges;
- именно он раздаёт `SELECT` read-роли и `SELECT/INSERT/UPDATE/DELETE` write-роли по схемам `public`, `system`, `analytics`, `audit`.
