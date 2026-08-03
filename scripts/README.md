# Scripts

Здесь будут жить служебные скрипты:

- валидация `portfolio.v1`;
- экспорт контента;
- проверка server fingerprint перед deploy;
- backup и cleanup;
- подготовка release-артефактов.

Текущий deploy-контур использует:

- `deploy/bootstrap-server.sh`
  Первичный bootstrap пустого Linux-сервера под Docker-based production.
- `deploy/remote-deploy.sh`
  Основной удаленный deploy: загрузка env, проверка server id, роли БД, миграции, nginx и HTTPS.
- `deploy/run-migrations.sh`
  Применение SQL-схемы и refresh grants через admin-role.
- `deploy/install-cert-renew-timer.sh`
  Создание `systemd`-timer для автоматического renewal сертификатов.
- `deploy/renew-certificates.sh`
  Реальный renewal Let's Encrypt и reload nginx.
