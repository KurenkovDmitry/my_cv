"""Тесты конфигурации backend."""

from app.config.settings import Settings


def test_settings_strip_trailing_slash() -> None:
    """Проверяет нормализацию origin-значений."""

    settings = Settings(
        PUBLIC_FRONTEND_ORIGIN="http://localhost:5173/",
        ADMIN_FRONTEND_ORIGIN="http://localhost:5174/",
    )

    assert settings.allowed_origins == ["http://localhost:5173", "http://localhost:5174"]


def test_settings_build_database_role_urls() -> None:
    """Проверяет, что DSN для read/write/admin ролей собираются из granular env."""

    settings = Settings(
        POSTGRES_HOST="postgres",
        POSTGRES_PORT=5432,
        POSTGRES_DB_NAME="portfolio",
        DB_APP_READ_USERNAME="portfolio_read",
        DB_APP_READ_PASSWORD="read-secret",
        DB_APP_WRITE_USERNAME="portfolio_write",
        DB_APP_WRITE_PASSWORD="write-secret",
        DB_APP_ADMIN_USERNAME="portfolio_admin",
        DB_APP_ADMIN_PASSWORD="admin-secret",
        POSTGRES_SUPERUSER_NAME="portfolio_bootstrap",
        POSTGRES_SUPERUSER_PASSWORD="bootstrap-secret",
    )

    assert settings.database_read_url == "postgresql+asyncpg://portfolio_read:read-secret@postgres:5432/portfolio"
    assert settings.database_write_url == "postgresql+asyncpg://portfolio_write:write-secret@postgres:5432/portfolio"
    assert settings.database_admin_url == "postgresql+asyncpg://portfolio_admin:admin-secret@postgres:5432/portfolio"
    assert settings.database_bootstrap_url == "postgresql+asyncpg://portfolio_bootstrap:bootstrap-secret@postgres:5432/portfolio"
    assert settings.database_url == settings.database_write_url
