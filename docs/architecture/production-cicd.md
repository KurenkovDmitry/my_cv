# Production CI/CD

## Что делает новый контур

- `CI` запускает:
  - `npm run typecheck`;
  - `npm test`;
  - `pytest` для backend;
  - `npm audit`, `pip-audit` и `Trivy` как машинную проверку известных уязвимостей и опасных misconfig.
- `CD`:
  - стартует автоматически после успешного `CI` на `main`;
  - умеет ручной `workflow_dispatch` для первого bootstrap пустого сервера;
  - собирает production-образы `api` и `nginx`;
  - переносит их на сервер по SSH;
  - поднимает `postgres`, `redis`, `api`, `nginx`, миграции и grants;
  - выпускает Let's Encrypt сертификат для `kurenkovdmitrii.ru`;
  - ставит `systemd`-timer на автоматический renewal.

## DNS и cloud firewall

До первого deploy:

1. Добавить `A`-запись `kurenkovdmitrii.ru` на IP сервера.
2. Открыть во внешнем cloud firewall:
   - `22/tcp`;
   - `80/tcp`;
   - `443/tcp`.

## GitHub Environment

Создать environment `production` и положить туда:

Рекомендуется сразу включить:

- required reviewers для deploy в production;
- запрет на self-review, если вы используете отдельный рабочий GitHub-аккаунт для релизов;
- environment-scoped secrets, а не repository-wide secrets.

### Variables

- `DEPLOY_HOST`
  Адрес сервера.
- `DEPLOY_PORT`
  Обычно `22`.
- `DEPLOY_USER`
  Linux-пользователь для deploy по SSH.
- `PRODUCTION_DOMAIN`
  Для текущего контура: `kurenkovdmitrii.ru`.
- `ADMIN_BASE_PATH`
  Для текущего контура: `/admin/`.
- `VITE_DYNAMIC_BACKDROP`
  Обычно `true`.

### Secrets

- `DEPLOY_SSH_PRIVATE_KEY`
  Приватный ключ, которым GitHub Actions подключается к серверу.
- `DEPLOY_SSH_KNOWN_HOSTS`
  Строка `known_hosts` для strict host key checking. Это первый уровень проверки, что workflow подключается именно к вашему серверу.
- `DEPLOY_SERVER_ID`
  Случайный серверный маркер, например `openssl rand -hex 32`. Это второй уровень проверки: deploy сверяет файл `/etc/portfolio/deploy-server-id` с этим секретом.
- `LETSENCRYPT_EMAIL`
  Email для Let's Encrypt.
- `PRODUCTION_ENV_FILE`
  Многострочный секрет с production `.env`. За основу взять [production.env.example](/C:/Users/DimaK/Desktop/Arbiten/cv/my_cv/config/production.env.example).

## Как подготовить `DEPLOY_SSH_KNOWN_HOSTS`

Нужно не просто сделать `ssh-keyscan`, а сверить ключ сервера:

1. На сервере:
   - `sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256`
2. На своей локальной машине:
   - `ssh-keyscan -t ed25519 kurenkovdmitrii.ru`
3. Убедиться, что fingerprint совпадает.
4. Результат `ssh-keyscan` целиком положить в secret `DEPLOY_SSH_KNOWN_HOSTS`.

## Первый deploy

1. Добавить SSH-ключ на сервер.
2. Заполнить environment `production`.
3. Ручной запуск workflow `CD`:
   - `bootstrap_server = true`
   - `git_ref = main`

Первый запуск:

- установит Docker на пустой сервер;
- создаст `/opt/portfolio/...`;
- создаст `/etc/portfolio/deploy-server-id`, если его еще нет;
- поднимет HTTP nginx;
- выпустит сертификат;
- переключит nginx на HTTPS.

## Последующие deploy

После этого deploy на `main` идет автоматически только если `CI` завершился успешно.

## Что лежит в `PRODUCTION_ENV_FILE`

Минимально нужно задать:

- origins и API URLs на `https://kurenkovdmitrii.ru`;
- три DB-роли и bootstrap-superuser;
- `AUTH_RATE_LIMIT_KEY_PEPPER`;
- `BACKUP_STORAGE_PATH=/opt/portfolio/backups`;
- аналитические retention и throttling limits;
- `DOMAIN_NAME=kurenkovdmitrii.ru`;
- `ENABLE_HTTPS=true`;
- `ADMIN_BASE_PATH=/admin`.

## Проверка сервера "это точно мой"

В контуре две проверки:

1. SSH идет только при совпадении pinned host key из `DEPLOY_SSH_KNOWN_HOSTS`.
2. Уже на сервере deploy сверяет `/etc/portfolio/deploy-server-id` с `DEPLOY_SERVER_ID`.

Если хотя бы одна проверка не совпадает, выкладка завершается с ошибкой.
