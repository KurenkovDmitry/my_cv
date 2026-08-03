# Database Access Roles

## Зачем это нужно

Для проекта сразу закладываются три прикладные роли БД плюс bootstrap-superuser:

- `bootstrap-superuser`
- `app-read`
- `app-write`
- `app-admin`

Это нужно, чтобы:

- публичный read-path не ходил в БД правами записи;
- обычные mutation-path сценарии не получали права миграций и DDL;
- partition management, grant refresh и миграции выполнялись отдельной admin-ролью;
- логины и пароли не были захардкожены в коде.

## Роли

### 1. Bootstrap superuser

Используется только для:

- первого старта контейнера PostgreSQL;
- создания `app-read`, `app-write`, `app-admin`;
- первичного назначения owner на app-базу.

В backend runtime эту роль использовать не надо.

### 2. App read

Используется для:

- SSR/read-only snapshot запросов;
- чтения опубликованного контента;
- чтения аналитических агрегатов;
- чтения backup/import metadata.

Права:

- `CONNECT` на БД;
- `USAGE` на схемы;
- `SELECT` на таблицы.

### 3. App write

Используется для:

- сохранения draft;
- публикации snapshot;
- обновления analytics daily/total агрегатов;
- обновления служебного state;
- audit insert-path.

Права:

- `CONNECT` на БД;
- `USAGE` на схемы;
- `SELECT, INSERT, UPDATE, DELETE` на таблицы;
- `USAGE, SELECT` на sequences.

### 4. App admin

Используется для:

- миграций;
- grant refresh;
- создания и удаления monthly partitions;
- сервисных maintenance-операций;
- import/backup административного контура.

Права:

- полный набор прав на app-базу;
- owner/DDL-путь для прикладной схемы.

## Где это зафиксировано в репозитории

- env-модель: [.env.example](C:\Users\DimaK\Desktop\Arbiten\cv\my_cv\.env.example)
- bootstrap ролей: [00-bootstrap-app-roles.sh](C:\Users\DimaK\Desktop\Arbiten\cv\my_cv\infrastructure\postgres\init\00-bootstrap-app-roles.sh)
- refresh grants: [refresh-app-grants.sh](C:\Users\DimaK\Desktop\Arbiten\cv\my_cv\scripts\postgres\refresh-app-grants.sh)
- backend settings: [settings.py](C:\Users\DimaK\Desktop\Arbiten\cv\my_cv\backend\app\config\settings.py)
- session factories: [session.py](C:\Users\DimaK\Desktop\Arbiten\cv\my_cv\backend\app\database\session.py)
