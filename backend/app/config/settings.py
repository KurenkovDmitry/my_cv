"""Централизованная конфигурация backend."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Безопасные настройки backend без хранения секретов в коде."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    public_frontend_origin: str = Field(default="http://localhost:5173", alias="PUBLIC_FRONTEND_ORIGIN")
    admin_frontend_origin: str = Field(default="http://localhost:5174", alias="ADMIN_FRONTEND_ORIGIN")
    allowed_methods_csv: str = Field(
        default="GET,POST,PUT,PATCH,DELETE,OPTIONS",
        alias="CORS_ALLOWED_METHODS",
    )
    allowed_headers_csv: str = Field(
        default="Authorization,Content-Type,X-CSRF-Token,X-Request-ID",
        alias="CORS_ALLOWED_HEADERS",
    )

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db_name: str = Field(default="portfolio", alias="POSTGRES_DB_NAME")
    postgres_superuser_name: str = Field(default="portfolio_bootstrap", alias="POSTGRES_SUPERUSER_NAME")
    postgres_superuser_password: str = Field(default="change-me-bootstrap", alias="POSTGRES_SUPERUSER_PASSWORD")
    database_read_username: str = Field(default="portfolio_app_read", alias="DB_APP_READ_USERNAME")
    database_read_password: str = Field(default="change-me-read", alias="DB_APP_READ_PASSWORD")
    database_write_username: str = Field(default="portfolio_app_write", alias="DB_APP_WRITE_USERNAME")
    database_write_password: str = Field(default="change-me-write", alias="DB_APP_WRITE_PASSWORD")
    database_admin_username: str = Field(default="portfolio_app_admin", alias="DB_APP_ADMIN_USERNAME")
    database_admin_password: str = Field(default="change-me-admin", alias="DB_APP_ADMIN_PASSWORD")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    public_portfolio_ttl_seconds: int = Field(default=300, alias="REDIS_PUBLIC_PORTFOLIO_TTL_SECONDS")
    project_list_ttl_seconds: int = Field(default=300, alias="REDIS_PROJECT_LIST_TTL_SECONDS")
    analytics_session_daily_retention_days: int = Field(
        default=548,
        alias="ANALYTICS_SESSION_DAILY_RETENTION_DAYS",
    )
    analytics_section_view_daily_retention_days: int = Field(
        default=365,
        alias="ANALYTICS_SECTION_VIEW_DAILY_RETENTION_DAYS",
    )
    analytics_section_click_daily_retention_days: int = Field(
        default=365,
        alias="ANALYTICS_SECTION_CLICK_DAILY_RETENTION_DAYS",
    )
    analytics_event_dedupe_window_seconds: int = Field(
        default=30,
        alias="ANALYTICS_EVENT_DEDUPE_WINDOW_SECONDS",
    )
    analytics_spike_threshold: int = Field(
        default=20,
        alias="ANALYTICS_SPIKE_THRESHOLD",
    )
    analytics_spike_window_seconds: int = Field(
        default=60,
        alias="ANALYTICS_SPIKE_WINDOW_SECONDS",
    )
    audit_log_retention_days: int = Field(default=90, alias="AUDIT_LOG_RETENTION_DAYS")
    backup_storage_path: str = Field(
        default="/opt/portfolio/backups",
        alias="BACKUP_STORAGE_PATH",
    )
    import_candidate_retention_days: int = Field(
        default=30,
        alias="IMPORT_CANDIDATE_RETENTION_DAYS",
    )
    enable_grafana_integration: bool = Field(
        default=False,
        alias="ENABLE_GRAFANA_INTEGRATION",
    )

    auth_login_rate_limit_count: int = Field(default=5, alias="AUTH_LOGIN_RATE_LIMIT_COUNT")
    auth_login_rate_limit_window_seconds: int = Field(
        default=900,
        alias="AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    )
    auth_ip_rate_limit_count: int = Field(default=20, alias="AUTH_IP_RATE_LIMIT_COUNT")
    auth_ip_rate_limit_window_seconds: int = Field(
        default=900,
        alias="AUTH_IP_RATE_LIMIT_WINDOW_SECONDS",
    )
    auth_api_rate_limit_count: int = Field(default=200, alias="AUTH_API_RATE_LIMIT_COUNT")
    auth_api_rate_limit_window_seconds: int = Field(
        default=60,
        alias="AUTH_API_RATE_LIMIT_WINDOW_SECONDS",
    )
    auth_lockout_base_seconds: int = Field(default=60, alias="AUTH_LOCKOUT_BASE_SECONDS")
    auth_lockout_max_seconds: int = Field(default=3600, alias="AUTH_LOCKOUT_MAX_SECONDS")
    auth_rate_limit_key_pepper: str = Field(default="change-me", alias="AUTH_RATE_LIMIT_KEY_PEPPER")

    @property
    def allowed_origins(self) -> list[str]:
        """Возвращает список разрешённых origin без wildcard-значений."""

        return [self.public_frontend_origin, self.admin_frontend_origin]

    @property
    def allowed_methods(self) -> list[str]:
        """Разбирает список методов для CORS."""

        return [method.strip() for method in self.allowed_methods_csv.split(",") if method.strip()]

    @property
    def allowed_headers(self) -> list[str]:
        """Разбирает список заголовков для CORS."""

        return [header.strip() for header in self.allowed_headers_csv.split(",") if header.strip()]

    @property
    def database_read_url(self) -> str:
        """DSN read-only роли приложения."""

        return self._build_asyncpg_url(self.database_read_username, self.database_read_password)

    @property
    def database_write_url(self) -> str:
        """DSN write-роли приложения."""

        return self._build_asyncpg_url(self.database_write_username, self.database_write_password)

    @property
    def database_admin_url(self) -> str:
        """DSN admin-роли приложения для миграций, partition-management и grant-sync."""

        return self._build_asyncpg_url(self.database_admin_username, self.database_admin_password)

    @property
    def database_bootstrap_url(self) -> str:
        """DSN bootstrap-superuser для первичного провижининга ролей и БД."""

        return self._build_asyncpg_url(self.postgres_superuser_name, self.postgres_superuser_password)

    @property
    def database_url(self) -> str:
        """Совместимый alias. По умолчанию backend работает через write-role."""

        return self.database_write_url

    def _build_asyncpg_url(self, username: str, password: str) -> str:
        """Собирает asyncpg DSN из granular env-переменных."""

        return (
            f"postgresql+asyncpg://{username}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db_name}"
        )

    @field_validator("public_frontend_origin", "admin_frontend_origin")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        """Не даёт запустить production с небезопасными origin."""

        if value == "*":
            raise ValueError("Wildcard origin запрещён для production-контура.")

        return value.rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Кэширует настройки на время жизни процесса."""

    return Settings()
